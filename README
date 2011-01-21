# cedric, a testing tool

The purpose of cedric is simple: it allows you to run multiple regex matches over a series of HTTP requested pages and lets you know if they fail. It does a few fancy things as well (cookie saving across tests, SSL support, and more!), but that's pretty much it. Let me be very clear: this is not meant to replace any unit testing framework. This is a tool for testing your applications as a whole, a little bit more peace of mind if you will. It hasn't been designed to be run after every save, rather you should run it just before you do a commit or a push.

Also, this is no [selenium](http://seleniumhq.org/). There isn't and won't ever be anything involving a browser in this.

## Useful features

* Standard python regex format (with . matching all characters through re.DOTALL)
* SSL support
* Cookies are saved between all tests in the same yaml file
* Data can be POST-ed (combined with saved cookies, you can logon to websites)

## Using cedric

cd to your favourite folder.

	$ git clone git@github.com:jeremyherbert/cedric.git

Now in that folder, edit the example yaml file. You can always write your own too, it's all explained in the file!

	$ python run_cedric.py example.yml

and you get:

	Running cedric example file (example.yml)...
	..
	
	Test report for example.yml:
	2 tests (with 11 regexes) run; 2 tests passed, 0 warnings, 0 failed

or if a test fails:

	Running cedric example file (example.yml)...
	.F
	
	Test report for example.yml:
	2 tests (with 11 regexes) run; 1 tests passed, 0 warnings, 1 failed
	
	Failed tests:
	    testSomeMore:
	        isInProgress+

or if there was a problem with the page:

	Running cedric example file (example.yml)...
	.W
	
	Test report for example.yml:
	2 tests (with 7 regexes) run; 1 tests passed, 1 warnings, 0 failed
	(note: some tests ended with warnings; the results for these tests may be invalid)
	
	Warned tests:
	    testSomeMore: HTTPError encountered with code 404


## Drop to PDB

It can sometime be annoying to write regexes and have nothing to test with. If you pass the -p flag to cedric, you will drop into a nice pdb interpreter when the first test fails so you can play around:

	Running cedric example file (example.yml)...
	.
	
	Test failed, dropping to PDB. You might find the following variables useful:
	
	self.page               the http requested data
	self.name               the test name
	
	regex                   the regex that failed
	name                    the regex name
	
	Current url: http://jeremyherbert.net/get/cnc
	Current regex name: isInProgress+
	Current regex: \{in progresss\}
	
	
	> /home/jeremy/cedric/cedric/cedric.py(285)run()
	-> for name, regex in self.patterns.items():
	(Pdb) re.search("\{in progress\}", self.page)
	<_sre.SRE_Match object at 0x9799288>
	(Pdb) 
	