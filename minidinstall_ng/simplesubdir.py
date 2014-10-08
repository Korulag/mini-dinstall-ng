
class SimpleSubdirArchiveDirIndexer(ArchiveDirIndexer):

    def __init__(self, *args, **kwargs):
        apply(ArchiveDirIndexer.__init__, [self] + list(args), kwargs)
        for arch in list(self._arches) + ['source']:
            target = os.path.join(self._dir, arch)
            do_mkdir(target)

    def _index_impl(self, arches, force=None):
        for arch in arches:
            dirmtime = os.stat(self._relpath(arch))[stat.ST_MTIME]
            if arch != 'source':
                pkgsfile = self._relpath(arch, 'Packages')
                if force or (not os.access(pkgsfile, os.R_OK)) or dirmtime > os.stat(pkgsfile)[stat.ST_MTIME]:
                    self._logger.info('Generating Packages file for %s...' % (arch,))
                    self._make_packagesfile(self._relpath(arch))
                    self._logger.info('Packages generation complete')
                else:
                    self._logger.info('Skipping generation of Packages file for %s' % (arch,))

            else:
                pkgsfile = self._relpath(arch, 'Sources')
                if force or (not os.access(pkgsfile, os.R_OK)) or dirmtime > os.stat(pkgsfile)[stat.ST_MTIME]:
                    self._logger.info('Generating Sources file for %s...' % (arch,))
                    self._make_sourcesfile(self._relpath('source'))
                    self._logger.info('Sources generation complete')
                else:
                    self._logger.info('Skipping generation of Sources file for %s' % (arch,))

    def _gen_release_impl(self, arches, force):
        for arch in arches:
            targetname = self._relpath(arch, 'Release')
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
            uncompr_indexfile = os.path.join(arch, 'Packages')
            indexfiles =  [uncompr_indexfile]
            comprexts = ['.gz', '.bz2']
            for ext in comprexts:
                indexfiles = indexfiles + [uncompr_indexfile + ext]
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
                continue
            self._logger.info("Generating Release...")
            if no_act:
                self._logger.info("Release generation complete")
                return
            self._write_releasefile(tmpname)

            if self._sign_releasefile(os.path.basename(tmpname), self._abspath(arch)):
                os.rename(tmpname, targetname)
                self._logger.info("Release generation complete")

    def _in_archdir(self, *args):
        return apply(lambda x,self=self: self._abspath(x), args)

    def _get_dnotify_dirs(self):
        return map(lambda x, self=self: self._abspath(x), self._arches + ['source'])

    def _get_all_indexfiles(self):
        return map(lambda arch: os.path.join(arch, 'Packages'), self._arches) + ['source/Sources']


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
