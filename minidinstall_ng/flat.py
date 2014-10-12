class FlatArchiveDirIndexer(ArchiveDirIndexer):
    def __init__(self, *args, **kwargs):
        ArchiveDirIndexer.__init__(self, *args, **kwargs)

    def _index(self, arches, force=None):
        pkgsfile = self._abspath('Packages')
        dirmtime = os.stat(self._relpath()).st_mtime
        if force or (not os.access(pkgsfile, os.R_OK)) or dirmtime > os.stat(pkgsfile).st_mtime:
            self._logger.info('Generating Packages file...')
            self._make_packagesfile(self._relpath())
            self._logger.info('Packages generation complete')
        else:
            self._logger.info('Skipping generation of Packages file')
        pkgsfile = self._abspath('Sources')
        if force or (not os.access(pkgsfile, os.R_OK)) or dirmtime > os.stat(pkgsfile).st_mtime:
            self._logger.info('Generating Sources file...')
            self._make_sourcesfile(self._relpath())
            self._logger.info('Sources generation complete')
        else:
            self._logger.info('Skipping generation of Sources file')


    def _gen_release(self, arches, force):
        release_file = self._abspath('Release')
        if not self._generate_release:
            if os.access(release_file, os.R_OK):
                self._logger.info("Release generation disabled, removing existing Release file")
                try:
                    os.unlink(release_file)
                except OSError, e:
                    pass
            return
        tmpname = release_file + tmp_new_suffix
        if self.release_needed:
            self._logger.info("Release file is up to date.")
            return
        self._logger.info("Generating Release...")
        if no_act:
            self._logger.info("Release generation complete")
            return
        f = open(tmpname, 'w')
        self._write_origin_to(f)
        self._write_label_to(f)
        self._write_suite_to(f)
        codename = self.config.release_codename
        if not codename:
            codename = suite
        f.write('Codename: ' + codename + '\n')
        self._write_no_automatic_to(f)
        self._write_date_to(f)
        f.write('Architectures: ' + string.join(self._arches, ' ') + '\n')
        if self._release_description:
            f.write('Description: ' + self._release_description + '\n')
        self._hash_files_to(indexfiles, f)
        f.close()
        if self._sign_releasefile(tmpname, self._abspath()):
            os.rename(tmpname, release_file)
            self._logger.info("Release generation complete")

    def _in_archdir(self, *args):
        return apply(lambda x,self=self: self._abspath(x), args[1:])

    def _get_dnotify_dirs(self):
        return [self._dir]

    def _get_uncompressed_indexfiles(self):
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