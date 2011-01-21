# cedric.py

import pdb, traceback, sys

import os, sys, re
import urllib, urllib2, cookielib
import yaml 

from odict import Odict

from exceptions import *

usage = """Cedric - a regex-based http testing tool

usage: run_cedric.py [options] [test1.yaml] [test2.yaml] ...

options:
    -h, --help                              Show this text
    -v, --verbose                           Print all debug messages
    -d [folder], --dump [folder]            If a test fails occurs, dump the
                                            HTTP data to a file in the folder
    -p, --pdb                               Drop to pdb on test failure or exception
"""

pdb_msg = """

Test failed, dropping to PDB. You might find the following variables useful:

self.page               the http requested data
self.name               the test name

regex                   the regex that failed
name                    the regex name
"""

test_files = []
verbose = True
dump_folder = ''
pdb_drop = False
regex_count = 0

def enum(**enums):
    return type('Enum', (), enums)
    
TestStatus = enum(OK='Ok', WARN='Warning', FAILURE='Error')

def print_v(msg, newline=True):
    if verbose:
        if newline:
            print msg
        else:
            print msg,

class Tester(object):
    """
    The Tester class manages the parsing of the test file and the outputting of the test results.
    """
    def __init__(self, test_file, **kwargs):
        self.test_file = test_file
        self.full_dict = {}
        self.test_dict = {}
        
        self.cookiejar = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        
        self.tests = []
        
        if kwargs.get('load'):
            self.load()
        
        if kwargs.get('run'):
            self.run()
        
    def __str__(self):
        return "Cedric tester: %s" % self.test_file
        
    def load(self):
        """
        load() -> None
        
        Loads the configuration file and sorts the tests into the correct order.
        """
        print_v("Loading test file: %s" % self.test_file)
        if not os.path.exists(self.test_file):
            raise IOError("Test file not found")
            
        f = open(self.test_file, 'r')
        yaml_data = f.read()
        self.full_dict = yaml.load(yaml_data)
        self.test_dict = self.full_dict.get('tests')
        f.close()
        
        self.validate()
        
        # now we need to sort the dict, even though the YAML spec doesn't allow sorted trees
        key_list = []
        
        for key in self.test_dict.keys():
            key_list.append((yaml_data.find(key + ":"), key))
        key_list.sort() # sort by the first element of the tuple
        
        temp_dict = self.test_dict
        self.test_dict = Odict()
        for loc, key in key_list:
            self.test_dict[key] = temp_dict[key]
            
        print_v("Loaded tests: %s" % self.full_dict['meta']['name'])
        self.base_url = self.full_dict['meta']['base_url']
        
    def validate(self):
        """
        validate() -> None
        
        Validates that the configuration file has most of the bits that are required.
        """
        print_v("Validating test file...")
        if self.full_dict == {}:
            raise ValidationError("Test file is empty: %s" % self.test_file)
        
        if not self.full_dict.get('meta'):
            raise ValidationError("Test file does not have a meta key: %s" % self.test_file)
        
        if not self.full_dict['meta'].get('name'):
            raise ValidationError("Test file is missing a name: %s" % self.test_file)
        
        if not self.full_dict['meta'].get('base_url'):
            raise ValidationError("Test file is missing a base url: %s" % self.test_file)
            
        if not self.full_dict.get('tests'):
            raise ValidationError("No tests")
    
    def run(self):
        """
        run() -> None
        
        Run all of the tests in the loaded test file.
        """
        
        print "Running %s (%s)..." % (self.full_dict['meta']['name'], self.test_file)
        
        all_test = self.test_dict.get('all', {})
        
        self.tests = []
        count = {'P': 0, 'W': 0, 'F': 0}
        
        for name, test_data in self.test_dict.items():
            if name == 'all':
                  continue # ignore the all case
            
            if type(test_data.get('patterns')) != dict and type(all_test.get('patterns')) != dict:
                raise MalformedTestError('No patterns supplied')
            
            # dictionary merge
            elif test_data.get('patterns') and all_test.get('patterns') and type(test_data['patterns']) == dict and type(all_test['patterns']) == dict:
                patterns = dict(test_data['patterns'], **all_test['patterns'])
            elif test_data.get('patterns') and type(test_data['patterns']) == dict:
                patterns = test_data['patterns']
            elif type(all_test.get('patterns')) == dict:
                patterns = all_test['patterns']
            
            url = self.base_url + test_data['url']
            
            # encode post data
            post_data = ''
            if test_data.get('post') and type(test_data) == dict:
                post_data = urllib.urlencode(test_data['post'])
            elif test_data.get('post'):
                raise MalformedTestError("Invalid post data specified on test: %s" % name)

            test = Test(name, url, name[-1] == '*', post_data, patterns, self.opener, supress_all_patterns=test_data.get('supress_all_patterns'))
            test.run()
            
            sys.stdout.write(test.getStatusCode())
            sys.stdout.flush()
            if test.status == TestStatus.FAILURE:
                count['F'] += 1
            elif test.status == TestStatus.WARN:
                count['W'] += 1
            elif test.status == TestStatus.OK:
                count['P'] += 1
            
            self.tests.append(test)
        
        print "\n\nTest report for %s:" % self.test_file
        print "%i tests (with %i regexes) run; %i tests passed, %i warnings, %i failed" % (len(self.tests), regex_count, count['P'], count['W'], count['F'])
        
        if count['W']:
            print "(note: some tests ended with warnings; the results for these tests may be invalid)"
            print "\nWarned tests:"
            for test in self.tests:
                if test.status == TestStatus.WARN:
                    print "    %s: %s" % (test.name, test.status_msg)
                    
                    
        if count['F']:
            print "\nFailed tests:"
            for test in self.tests:
                if test.status == TestStatus.FAILURE:
                    print "    %s:" % test.name
                    for f in test.failures:
                        print "        %s" % f
                    print "\n"
                

class Test(object):
    """
    This class represents a single test block. It is responsible for downloading the HTTP page and 
    running all of the regex matches.
    """
    def __init__(self, name, url, ssl, post_data, patterns, opener, **kwargs):
        if not url:
            raise MalformedTestError("No url supplied")
        if len(patterns) == 0:
            raise MalformedTestError("No patterns supplied")
        if type(post_data) != str:
            raise MalformedTestError("POST data was not correctly encoded")

        self.name = name
        
        if ssl:
            self.url = "https://" + url
        else:
            self.url = "http://" + url
            
        self.post_data = post_data
        self.patterns = patterns
        self.opener = opener
        self.ssl = ssl
        
        self.supress = kwargs.get('supress_all_patterns')

        self.status = TestStatus.OK
        self.status_msg = ''
        
        self.failures = []
        self.warned = []

        # save the opener so we can have cookies work
        self.opener = opener
        
        print_v('Built test object "%s"' % self.name)

    def __str__(self):
        return "Test %s" % self.name

    def setStatus(self, status, msg=''):
        """
        setStatus(status, msg='') -> None
        
        Sets the status of the test.
        """
        self.status = status
        self.status_msg = msg
        
    def getStatusCode(self):
        """
        getStatusCode() -> str
        
        Gets a single character status code, useful in showing the overall test results
        """
        return {TestStatus.OK: '.', TestStatus.WARN: 'W', TestStatus.FAILURE: 'F'}[self.status]

    def run(self):
        """
        run() -> None
        
        Downloads the http data and runs all of the regex matches.
        """
        global regex_count
        
        try:
            print_v("Getting %s (POST data: \"%s\")" % (self.url, self.post_data))
            if self.post_data:
                self.page = self.opener.open(self.url, self.post_data).read()
            else:
                self.page = self.opener.open(self.url).read()
        except urllib2.HTTPError, e: # we want to catch any status errors so we can still test
            self.setStatus(TestStatus.WARN, "HTTPError encountered with code %s" % e.code)
            return
            
        if self.supress:
            print_v('Supressing patterns')
            return
            
        for name, regex in self.patterns.items():
            regex_count += 1
            
            print_v("Testing pattern %s: \"%s\"..." % (name, regex), False)
            match = re.search(regex, self.page, re.DOTALL)
            
            if (name[-1] == '+' and not match) or (name[-1] == '-1' and match):
                self.failures.append(name)
                self.setStatus(TestStatus.FAILURE)
                print_v('fail')
                
                if pdb_drop:
                    print pdb_msg
                    print "Current url: %s\nCurrent regex name: %s\nCurrent regex: %s\n\n" % (self.url, name, regex)
                    pdb.set_trace()
            elif name[-1] != '+' and name[-1] != '-':
                raise MalformedTestError("Regex has no success/failure attribute. Make sure the name ends in a + or a -.")
            else:
                print_v('pass')
            
                

def run_with_argv():
    """
    run_with_argv() -> None
    
    Runs cedric with the arguments passed on the command line
    """
    global test_files, verbose, dump_folder, pdb_drop
    test_files = []
    verbose = False
    dump_folder = ''
    
    # parse arguments
    for index, arg in enumerate(sys.argv):
        if arg == '-h' or arg == "--help":
            print usage
            sys.exit(0)
        elif arg == '-v' or arg == '--verbose':
            verbose = True
        elif arg == '-d' or arg == '--dump':
            if len(sys.argv) == arg:
                raise ArgumentError("Dump folder not specified")
            
            dump_folder = sys.argv[index+1]
            
            if not os.path.exists(dump_folder):
                raise ArgumentError("Dump folder does not exist: %s" % dump_folder)
        elif arg == '-p' or arg == '--pdb':
            pdb_drop = True
            
        elif arg[-4:] == ".yml" or arg[-5:] == ".yaml":
            test_files.append(arg)
            
    if len(test_files) == 0:
        raise ArgumentError("No test files specified")
    
    for f in test_files:
        if pdb_drop:
            try:
                t = Tester(f, load=True, run=True)
            except:
                type, value, tb = sys.exc_info()
                traceback.print_exc()
                pdb.post_mortem(tb)
        else:
            t = Tester(f, load=True, run=True)
        