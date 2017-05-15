#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-----------------------------------------------------------
# Copyright (c) 2011-2014
# wobe-systems GmbH
#
# A simple Python module to automate build steps on 
# multiple platforms.
#-----------------------------------------------------------

import os
from subprocess import call
import glob
import shutil
import re
import stat
import time


class WBSBuildBase(object):
    pass


class WBSToolBase(WBSBuildBase):

    def __init__(self, aengine, aname):
        WBSBuildBase.__init__(self)
        self.__engine = aengine
        self.__name = aname

    ## @property engine
    #  @brief [\b WBSBuildEngine] build engine
    #
    #  @par Access:
    #    read

    #  @cond NODOC
    @property
    def engine(self):
        return self.__engine
    #  @endcond

    ## @property name
    #  @brief [\b str] tool instance name
    #
    #  @par Access:
    #    read

    #  @cond NODOC
    @property
    def name(self):
        return self.__name
    #  @endcond

    def execute(self):
        assert False, "abstract error - pure virtual function call"


## @brief call a commandline command
class WBSCmdCall(WBSToolBase):

    def __init__(self, aengine, aname, cmd, path=None, exception=True):
        WBSToolBase.__init__(self, aengine, aname)
        self.__cmd = cmd
        if path:
            self.__path = self.engine.replace_var(path)
        else:
            self.__path = None
        self.__exception = exception

    def execute(self, param):
        lparam = self.engine.replace_var(param)
        if self.__path:
            cmd = '"%s" %s' % (os.path.join(self.engine.abspath(self.__path), self.__cmd), lparam)
        else:
            cmd = '%s %s' % (self.__cmd, lparam)

        print("exec %s : %s" % (self.name, cmd))

        #print(shlex.split(lparam))
        err = call(cmd, shell=True)

        #err = os.system(cmd)

        if err != 0:
            if self.__exception:
                raise Exception("error in %s: %s (%s)" % (self.name, cmd, err))
            else:
                print("warning: %s: %s (%s)" % (self.name, cmd, err))


## @brief Copy files to a destination whith full path creation
class WBSFullCopy(WBSToolBase):

    ## @brief Init WBSFullCopy.
    #
    #  @param aengine : [\b WBSBuildEngine] build engine
    #  @param aname   : [\b str]            tool name
    #  @param path    : [\b str][\em optional] base path
    def __init__(self, aengine, aname, path=None):
        WBSToolBase.__init__(self, aengine, aname)
        if path:
            self.__path = self.engine.replace_var(path)
        else:
            self.__path = None

    ## @brief Copy file(s)
    #
    #  @param asrc  : [\b str] Source filename or whildcards to copy specific files.
    #                          Wildcards are using unix match patterns. See python glob module for examples
    #  @param adest : [\b str] Destination path or relative path in base path.
    def execute(self, asrcdir, adest, recurse=False, rekcnt=0):

        if rekcnt > 20:
            raise Exception("maximum recursion depth reached")

        asrcdir = self.engine.replace_var(asrcdir)
        adest = self.engine.replace_var(adest)

        afilematch = os.path.basename(asrcdir)
        asrcdir = os.path.dirname(asrcdir)

        asrc = os.path.join(asrcdir, afilematch)

        files2copy = glob.glob(asrc)
        if len(files2copy) == 0:
            print("warning: no files found in %s -> nothing to do !" % asrc)
        else:
            print("single file copy")

        if self.__path:
            fdirname = os.path.join(self.__path, adest)
        else:
            fdirname = adest

        if not os.path.exists(fdirname):
            os.makedirs(adest)
            print("created %s" % fdirname)

        for lfile in files2copy:
            print(lfile)
            lfilename = os.path.basename(lfile)
            if os.path.isdir(lfile):
                print("info: %s is a directory" % lfile)
            else:
                ldpath = os.path.join(fdirname, lfilename)
                shutil.copyfile(lfile, ldpath)
                print("copied %s -> %s" % (lfile, ldpath))

        if recurse:
            litems = os.listdir(asrcdir)
            subdirs = []
            for item in litems:
                srcpath = os.path.join(asrcdir, item)
                if os.path.isdir(srcpath):
                    self.execute(os.path.join(srcpath, afilematch), os.path.join(adest, item), True, rekcnt+1)
                    subdirs.append(item)

            print(subdirs)


## @brief Check out svn repositories
class WBSSVNCheckout(WBSToolBase):

    ## @brief Init WBSSVNCheckout.
    #
    #  @param aengine : [\b WBSBuildEngine] build engine
    #  @param aname   : [\b str]            tool name
    #  @param repos   : [\b str]            repository
    def __init__(self, aengine, aname, path=None):
        WBSToolBase.__init__(self, aengine, aname)

    def execute(self, asrcfile, adestfile):
        pass

## @brief Clones a git repository from a given URL. When a specific branch, commit or tag is not stated
#         the Class will stay in the default branch with the latest commit.
class WBSGitCheckout(WBSToolBase):
    ## @brief Init WBSGitCheckout.
    #
    #  @param aengine : [\b WBSBuildEngine] build engine
    #  @param aname   : [\b str]            tool name
    #  @param path    : [\b str]            path
    def __init__(self, aengine, aname, path=None):
        WBSToolBase.__init__(self, aengine, aname)

    ## @brief Clones a repository
    #
    #  @param repositoryUrl : [\b str] URL to the Git repository that will be cloned
    #  @param checkout      : [\b str] Specifies the commit, tag or branch that will be checked out
    def execute(self, repositoryUrl, checkout="default"):

        srcdir = os.getcwd() # save source directory
        
        print("git clone " + repositoryUrl)
        call(["git", "clone", repositoryUrl])
        
        folder = self.extractFolderName(repositoryUrl)

        if checkout != "default":
            print ("Checkout: " + checkout)   # Tag or branch detected
            checkoutIsSet = True
        else:
            checkoutIsSet = False
            print ("Default branch.")
            os.chdir(folder)  # Enter Repository

        if checkoutIsSet:
            os.chdir(folder)  # Enter Repository
            print("Enter folder: " + folder);
            call(["git", "checkout", checkout])

        os.chdir(srcdir) # Go back to source directory

    ## @brief Extracts the folder name from a git URL
    #
    #  @param repositoryUrl : [\b Str]      URL of the Repository
    def extractFolderName(self, repositoryUrl):
        return repositoryUrl.split("/")[-1].strip(".git")



## @brief Rename files with regex search replace.
class WBSFileRename(WBSToolBase):

    ## @brief Init WBSSVNCheckout.
    #
    #  @param aengine : [\b WBSBuildEngine] build engine
    #  @param aname   : [\b str]            tool name
    #  @param repos   : [\b str]            repository
    def __init__(self, aengine, aname):
        WBSToolBase.__init__(self, aengine, aname)

    ## @brief Rename files.
    #
    #  @param apath    : [\b str] Path to files
    #  @param asearch  : [\b str] regex search pattern
    #  @param areplace : [\b str] replace string
    #  @param recurde  : [\b bool][\em optional] process subdirectories
    #  @param rekcnt   : [\b int][\em optional] recursion counter (internal use)
    def execute(self, apath, asearch, areplace, recurse=False, rekcnt=0):
        if rekcnt > 20:
            raise Exception("maximum recursion depth reached")

        apath = self.engine.replace_var(apath)
        asearch = self.engine.replace_var(asearch)
        areplace = self.engine.replace_var(areplace)

        litems = os.listdir(apath)
        for litem in litems:
            litempath = os.path.join(apath, litem)
            if os.path.isfile(litempath):
                newname = re.sub(asearch, areplace, litem, re.IGNORECASE)
                if litem != newname:
                    print("rename: %s -> %s" % (litem, newname))
                    os.rename(os.path.join(apath, litem), os.path.join(apath, newname))
            elif os.path.isdir(litempath) and recurse:
                self.execute(os.path.join(apath, litem), asearch, areplace, True, rekcnt+1)


## @brief Delete a directory and all subdirectories or a file.
class WBSDel(WBSToolBase):

    ## @brief Init WBSDelTree.
    #
    #  @param aengine : [\b WBSBuildEngine] build engine
    #  @param aname   : [\b str]            tool name
    def __init__(self, aengine, aname):
        WBSToolBase.__init__(self, aengine, aname)

    def changePermissionAndDelete(self, function, path, excinfo):

        os.chmod(path, stat.S_IWRITE)
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path, onerror=self.changePermissionAndDelete)

    def execute(self, apath, raise_errors=True):

        apath = self.engine.replace_var(apath)
        if os.path.isfile(apath):
            os.remove(apath)
            print(apath + " deleted")
        elif os.path.isdir(apath):
            shutil.rmtree(apath, onerror=self.changePermissionAndDelete)
            print(apath + " deleted")
        else:
            print(apath + " doesn't exists")




## @brief Check out svn repositories
class WBSProcessTemplate(WBSToolBase):

    ## @brief Init WBSSVNCheckout.
    #
    #  @param aengine : [\b WBSBuildEngine] build engine
    #  @param aname   : [\b str]            tool name
    def __init__(self, aengine, aname, regex="\&"):
        WBSToolBase.__init__(self, aengine, aname)
        self.__regex = regex

    def execute(self, srcfile, destfile, encode="ascii"):
        srcfile = self.engine.replace_var(srcfile)
        destfile = self.engine.replace_var(destfile)

        sfile = open(srcfile, "r", encoding=encode)
        dfile = open(destfile, "w", encoding=encode)
        lines = sfile.readlines()
        try:
            for sline in lines:

                print(sline)
                sline = self.engine.replace_var(sline, regex=self.__regex)
                dfile.write(sline)
        finally:
            dfile.close()
            sfile.close()


## @brief Search for regular expression and replace string.
class WBSFindReplace(WBSToolBase):

    ## @brief Init WBSSVNCheckout.
    #
    #  @param aengine : [\b WBSBuildEngine] build engine
    #  @param aname   : [\b str]            tool name
    def __init__(self, aengine, aname):
        WBSToolBase.__init__(self, aengine, aname)

    ## @brief find a string in a file and replace it.
    def execute(self, srcfile, destfile, aregex, areplace, encode="ascii"):
        srcfile = self.engine.replace_vars(srcfile)
        destfile = self.engine.replace_vars(destfile)

        sfile = open(srcfile, "r", encoding=encode)
        dfile = open(destfile, "w", encoding=encode)
        lines = sfile.readlines()
        try:
            for sline in lines:
                sline = re.sub(aregex, areplace, sline)
                print(sline)
                dfile.write(sline)
        finally:
            dfile.close()
            sfile.close()


## @brief run a python script
class WBSPyRun(WBSToolBase):

    def __init__(self, aengine, aname):
        WBSToolBase.__init__(self, aengine, aname)

    def execute(self, pyfile):
        pyfile = self.engine.replace_var(pyfile)
        print("exec python script: ", pyfile)
        self.__execbuild(pyfile)

    def __execbuild(self, ascript):
        with open(ascript) as f:
            code = compile(f.read(), ascript, 'exec')
            exec(code, {"global_build_tools" : self.engine.toolconf,
                        "global_build_vars"  : self.engine.buildvars,
                        "__file__"           : self.engine.abspath(ascript)}, None)


## @brief WBS build engine
class WBSBuildEngine(WBSBuildBase):

    ## @brief Constructor of WBSBuildEngine
    #
    #  @param gnames     : [\b dict] engine configuration
    #  @param buildsteps : [\b list][\em optional] a list of buildsteps to perform on run
    #  @param use_env    : [\b bool][\em optional] merge environment variables into build vars
    #  @param workdir    : [\b str][\em optional] working directory (absolute path required)
    def __init__(self, gnames, buildsteps=None, use_env=False, workdir=None):
        WBSBuildBase.__init__(self)

        self.__toolconf = {
            "cpy"         : WBSFullCopy,
            "del"         : WBSDel,
            "rename"      : WBSFileRename
        }

        if "global_build_tools" in gnames:
            if "build_tools" in gnames:
                self.__toolconf.update(gnames["build_tools"])
                self.__toolconf.update(gnames["global_build_tools"])
            else:
                self.__toolconf.update(gnames["global_build_tools"])
        else:
            self.__toolconf.update(gnames["build_tools"])

        if "global_build_vars" in gnames:
            if "build_vars" in gnames:
                self.__buildvars = gnames["build_vars"]
                self.__buildvars.update(gnames["global_build_vars"])
            else:
                self.__buildvars = gnames["global_build_vars"]
        else:
            self.__buildvars = gnames["build_vars"]

        if use_env:
            self.__buildvars.update(os.environ)

        self.__buildsteps = buildsteps

        if workdir is not None:
            workdir = self.replace_var(workdir)
            self.__workdir = workdir
        else:
            self.__workdir = None

    ## @property toolconf
    #  @brief [\b dict] build too configuration
    #
    #  @par Access:
    #    read

    #  @cond NODOC
    @property
    def toolconf(self):
        return self.__toolconf
    #  @endcond

    ## @property buildvars
    #  @brief [\b dict] build variables
    #
    #  @par Access:
    #    read

    #  @cond NODOC
    @property
    def buildvars(self):
        return self.__buildvars
    #  @endcond

    def __run_buildsteps(self, btools, asteps, rek=0):
        if rek > 10:
            raise Exception("maximum rekursion count reached")

        if asteps:
            for bstep in asteps:
                if isinstance(bstep, tuple):
                    btool = btools[bstep[0]]
                    btool.execute(*(bstep[1:]))
                elif isinstance(bstep, list):
                    self.__run_buildsteps(btools, bstep, rek+1)
                else:
                    raise Exception("invalid build step: ", bstep)

    def run(self):

        if self.__workdir is not None:
            curdir = os.getcwd()
            os.chdir(self.__workdir)
            print("Current directory: %s Working directory %s" % (curdir, self.__workdir))

        try:
            # create tools
            buildtools = {}
            for key, value in self.__toolconf.items():
                if isinstance(value, tuple):
                    buildtools[key] = value[0](self, key, *(value[1:]))
                    print("create tool: ", key, *(value[1:]))
                else:
                    buildtools[key] = value(self, key)
                    print("create tool: ", key)

            # run build steps
            self.__run_buildsteps(buildtools, self.__buildsteps)

        finally:
            if self.__workdir is not None:
                os.chdir(curdir)
                print("Directory %s restored" % curdir)

    ##  @brief Replace one or more tokens like %tokenname%.
    #
    #  @param line            :[\b string] the line in wich the token should be replaced
    #  @param regex           :[\b string][\em optiona] regular expression to match start/end marker
    #  @param token           :[\b PyDict] a dictionary of tokens and values
    #  @return                 [\b string] translated line
    def replace_var(self, line, regex="\&", token=None):
        ltoken = {}
        ltoken.update(self.__buildvars)
        if token is not None:
            ltoken.update(token)

        tx = line

        lregex = re.compile(regex)
        smatch = lregex.search(tx)
        while smatch:
            ematch = lregex.search(tx, smatch.end())
            if not ematch:
                raise Exception("no end marker found")

            varname = tx[smatch.end():ematch.start()]
            divider = tx[smatch.start():smatch.end()]

            tx = tx.replace("%s%s%s" % (divider, varname, divider), str(ltoken[varname]))
            smatch = lregex.search(tx)

        return tx

    ## @brief Convert a relative path to an absolute path.
    def abspath(self, relpath):
        if self.__workdir is not None:
            return os.path.normpath(os.path.join(self.__workdir, relpath))
        else:
            print("warning : path cannot be converted to abspath: ", relpath)
            return relpath
