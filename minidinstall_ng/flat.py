class FlatArchiveDirIndexer(ArchiveDirIndexer):
    def __init__(self, *args, **kwargs):
        ArchiveDirIndexer.__init__(self, *args, **kwargs)

    def _index_impl(self, arches, force=None):
        pkgsfile = self._abspath('Packages')
        dirmtime = os.stat(self._relpath())[stat.ST_MTIME]
        if force or (not os.access(pkgsfile, os.R_OK)) or dirmtime > os.stat(pkgsfile)[stat.ST_MTIME]:
            self._logger.info('Generating Packages file...')
            self._make_packagesfile(self._relpath())
            self._logger.info('Packages generation complete')
        else:
            self._logger.info('Skipping generation of Packages file')
        pkgsfile = self._abspath('Sources')
        if force or (not os.access(pkgsfile, os.R_OK)) or dirmtime > os.stat(pkgsfile)[stat.ST_MTIME]:
            self._logger.info('Generating Sources file...')
            self._make_sourcesfile(self._relpath())
            self._logger.info('Sources generation complete')
        else:
            self._logger.info('Skipping generation of Sources file')

    def _gen_release_impl(self, arches, force):
        targetname = self._abspath('Release')
        if not self._generate_release:
            if os.access(targetname, os.R_OK):
                self._logger.info("Release generation disabled, removing existing Release file")
                try:
                    os.unlink(targetname)
                except OSError, e:
                    pass
            return
        tmpname = targetname + tmp_new_suffix
        release_needed = 0
        uncompr_indexfiles = self._get_all_indexfiles()
        indexfiles = []
        comprexts = ['.gz', '.bz2']
        for index in uncompr_indexfiles:
            indexfiles = indexfiles + [index]
            for ext in comprexts:
                indexfiles = indexfiles + [index + ext]
        if os.access(targetname, os.R_OK):
            release_mtime = os.stat(targetname)[stat.ST_MTIME]
            for file in indexfiles:
                if release_needed:
                    break
            if os.stat(self._abspath(file))[stat.ST_MTIME] > release_mtime:
                release_needed = 1
        else:
            release_needed = 1

        if not release_needed:
            self._logger.info("Skipping Release generation")
            return
        self._logger.info("Generating Release...")
        if no_act:
            self._logger.info("Release generation complete")
            return
        f = open(tmpname, 'w')
        f.write('Origin: ' + self.config.release_origin + '\n')
        f.write('Label: ' + self._release_label + '\n')
        suite = self._release_suite
        if not suite:
            suite = self._name
        f.write('Suite: ' + suite + '\n')
        codename = self.config.release_codename
        if not codename:
            codename = suite
        f.write('Codename: ' + codename + '\n')
        if self._experimental_release:
            f.write('NotAutomatic: yes\n')
        f.write('Date: ' + time.strftime("%a, %d %b %Y %H:%M:%S UTC", time.gmtime()) + '\n')
        f.write('Architectures: ' + string.join(self._arches, ' ') + '\n')
        if self._release_description:
            f.write('Description: ' + self._release_description + '\n')
        self._hash_files_to(indexfiles, f)
        f.close()
        if self._sign_releasefile(tmpname, self._abspath()):
            os.rename(tmpname, targetname)
            self._logger.info("Release generation complete")

    def _in_archdir(self, *args):
        return apply(lambda x,self=self: self._abspath(x), args[1:])

    def _get_dnotify_dirs(self):
        return [self._dir]

    def _get_all_indexfiles(self):
        return ['Packages', 'Sources']



class FlatArchiveDir(ArchiveDir):

    indexer_class = FlatArchiveDirIndexer

    def _read_source_dir(self):
        return os.listdir(self._dir)

    def _read_arch_dir(self, arch):
        return os.listdir(self._dir)

    def _arch_target(self, arch, file):
        return self._abspath(file)

    def _source_target(self, file):
        return self._arch_target('source', file)

    def _get_package_versions(self):
        ret = []
        for file in self._abspath(''):
            match = debpackage_re.search(file)
            if match:
                ret.append((match.group(1), match.group(2), match.group(3)))
        return ret