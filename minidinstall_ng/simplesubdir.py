
class SimpleSubdirArchiveDirIndexer(ArchiveDirIndexer):

    def __init__(self, *args, **kwargs):
        apply(ArchiveDirIndexer.__init__, [self] + list(args), kwargs)
        for arch in list(self._arches) + ['source']:
            target = os.path.join(self._dir, arch)
            do_mkdir(target)

    def _index(self, arches, force=None):
        for arch in arches:
            dirmtime = os.stat(self._relpath(arch)).st_mtime
            if arch != 'source':
                pkgsfile = self._relpath(arch, 'Packages')
                if force or (not os.access(pkgsfile, os.R_OK)) or dirmtime > os.stat(pkgsfile).st_mtime:
                    self._logger.info('Generating Packages file for %s...' % (arch,))
                    self._make_packagesfile(self._relpath(arch))
                    self._logger.info('Packages generation complete')
                else:
                    self._logger.info('Skipping generation of Packages file for %s' % (arch,))

            else:
                pkgsfile = self._relpath(arch, 'Sources')
                if force or (not os.access(pkgsfile, os.R_OK)) or dirmtime > os.stat(pkgsfile).st_mtime:
                    self._logger.info('Generating Sources file for %s...' % (arch,))
                    self._make_sourcesfile(self._relpath('source'))
                    self._logger.info('Sources generation complete')
                else:
                    self._logger.info('Skipping generation of Sources file for %s' % (arch,))

    def _gen_release(self, arches, force):
        for arch in arches:
            release_file = self._relpath(arch, 'Release')
            if not self._generate_release:
                if os.access(release_file, os.R_OK):
                    self._logger.info("Release generation disabled, removing existing Release file")
                    try:
                        os.unlink(release_file)
                    except OSError, e:
                        pass
                return
            tmp_release_file = release_file + tmp_new_suffix
            if not self.release_needed:
                self._logger.info("Skipping Release generation")
                continue
            self._logger.info("Generating Release...")
            if no_act:
                self._logger.info("Release generation complete")
                return
            f = open(tmp_release_file, 'w')
            self._write_origin_to(f)
            self._write_label_to(f)
            self._write_suite_to(f)

            codename = self._release_codename
            if not codename:
                codename = suite
            f.write('Codename: ' + '%s/%s\n' % (codename, arch))
            self._write_no_automatic_to(f)
            self._write_date_to(f)
            f.write('Architectures: ' + arch + '\n')
            if self._release_description:
                f.write('Description: ' + self._release_description + '\n')
            self._hash_files_to(indexfiles, f)
            f.close()
            if self._sign_releasefile(os.path.basename(tmp_release_file), self._abspath(arch)):
                os.rename(tmp_release_file, release_file)
                self._logger.info("Release generation complete")

    def _in_archdir(self, *args):
        return apply(lambda x,self=self: self._abspath(x), args)

    def _get_dnotify_dirs(self):
        return map(lambda x, self=self: self._abspath(x), self._arches + ['source'])

    def _get_uncompressed_indexfiles(self):
        return [os.path.join(arch, 'Packages') for arch in self._arches] + ['source/Sources']


class SimpleSubdirArchiveDir(ArchiveDir):
    
    indexer_class = SimpleSubdirArchiveDirIndexer

    def __init__(self, *args, **kwargs):
        apply(ArchiveDir.__init__, [self] + list(args), kwargs)
        for arch in list(self._arches) + ['source']:
            target = os.path.join(self._dir, arch)
            do_mkdir(target)

    def _read_source_dir(self):
        return os.listdir(self._abspath('source'))

    def _read_arch_dir(self, arch):
        return os.listdir(self._abspath(arch))

    def _arch_target(self, arch, file):
        return self._abspath(arch, file)

    def _source_target(self, file):
        return self._arch_target('source', file)

    def _get_package_versions(self):
        ret = []
        for arch in self._arches:
            for file in self._read_arch_dir(arch):
                match = debpackage_re.search(file)
                if match:
                    ret.append((match.group(1), match.group(2), match.group(3)))
        return ret
