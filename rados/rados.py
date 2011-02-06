"""librados Python ctypes wrapper
@author: Hannu Valtonen <hannu.valtonen@ormod.com
"""
from ctypes import CDLL, c_char_p, c_size_t, c_void_p, create_string_buffer, byref

class RadosError(Exception):
    pass

class ObjectNotFound(Exception):
    pass

class WriteError(Exception):
    pass

class IncompleteWriteError(Exception):
    pass
def object_deleted(method):
    def wrapper(self, *args, **kwargs):
        try:
            if self.deleted == False:
                return method(self, *args, **kwargs)
            else:
                raise ObjectNotFound("Object %s has been deleted" % self.oid)
        except:
            raise
    wrapper.__doc__ = method.__doc__
    wrapper.__name__ = method.__name__
    return wrapper

class Rados(object):
    """librados python wrapper"""
    def __init__(self, librados_path = '/usr/lib/librados.so.1.0.0'):
        self.librados = CDLL(librados_path)
        self.librados.rados_initialize(None)

    def de_initialize(self):
        self.librados.rados_deinitialize()

    def create_pool(self, pool_name):
        ret = self.librados.rados_create_pool(c_char_p(pool_name))
        if ret < 0:
            raise RadosError("pool %s couldn't be created" % pool_name)

    def delete_pool(self, pool):
        ret = self.librados.rados_delete_pool(pool)
        if ret < 0:
            raise RadosError("pool couldn't be deleted")

    def open_pool(self, pool_name):
        pool = c_void_p()
        ret = self.librados.rados_open_pool(c_char_p(pool_name), byref(pool))
        if ret < 0:
            raise RadosError("pool %s couldn't be opened" % pool_name)
        return RadosPool(self.librados, pool)

    def close_pool(self, pool):
        ret = self.librados.rados_close_pool(pool)
        if ret < 0:
            raise RadosError("pool couldn't be closed")

class RadosPool(object):
    """Pool object"""
    def __init__(self, librados, pool):
        self.librados = librados
        self.pool = pool
        self.deleted = False
    
    @object_deleted
    def get_object(self, key):
        return RadosObject(self, key)

    @object_deleted
    def write(self, key, string_to_write, offset = 0):
        length = len(string_to_write)
        ret = self.librados.rados_write(self.pool, c_char_p(key), c_size_t(offset), c_char_p(string_to_write), c_size_t(length))
        if ret == length:
            return ret
        elif ret < 0:
            raise WriteError("Write failed completely")
        elif ret < length:
            raise IncompleteWriteError("Wrote only %ld/%ld bytes" % (ret, length))
        else:
            raise RadosError("something weird happened while writing")
    
    @object_deleted
    def read(self, key, offset = 0, length = 8192):
        ret_buf = create_string_buffer(length)
        ret = self.librados.rados_read(self.pool, c_char_p(key), c_size_t(offset), ret_buf, c_size_t(length))
        if ret < 0:
            raise RadosError("Read failure, object doesn't exist?")
        return ret_buf.value

    @object_deleted
    def remove_object(self, key):
        ret = self.librados.rados_remove(self.pool, c_char_p(key))
        if ret < 0:
            raise RadosError("Delete failure")
        return True

class RadosObject(object):
    """Rados object wrapper, makes the object look like a file"""
    def __init__(self, pool, key):
        self.oid = key
        self.pool = pool
        self.offset = 0
        self.deleted = False

    @object_deleted
    def read(self, length = 1024*1024):
        ret = self.pool.read(self.oid, self.offset, length)
        self.offset += len(ret)
        return ret

    @object_deleted
    def write(self, string_to_write):
        ret = self.pool.write(self.oid, string_to_write, self.offset)
        self.offset += ret
        return ret

    @object_deleted
    def remove(self):
        self.pool.remove_object(self.oid)
        self.deleted = True

    @object_deleted
    def seek(self, position):
        self.offset = position
