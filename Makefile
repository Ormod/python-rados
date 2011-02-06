deb: 
	dpkg-buildpackage -A -uc -us
clean:         
	$(RM) -r *.egg-info/ build/ dist/

