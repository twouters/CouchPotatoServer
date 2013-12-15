from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode, sp
from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library, FileType
from couchpotato.environment import Env
import subliminal
import traceback

log = CPLog(__name__)


class Subtitle(Plugin):

    services = ['addic7ed', 'opensubtitles', 'podnapisi', 'thesubdb', 'tvsubtitles']
    subliminal.cache_region.configure('dogpile.cache.dbm', arguments={'filename': Env.get('cache_dir') + '/subliminal_cache.dbm'})

    def __init__(self):
        addEvent('renamer.before', self.searchSingle)

    def searchLibrary(self):

        # Get all active and online movies
        db = get_session()

        library = db.query(Library).all()
        done_status = fireEvent('status.get', 'done', single = True)

        for movie in library.movies:

            for release in movie.releases:

                # get releases and their movie files
                if release.status_id is done_status.get('id'):

                    files = []
                    for file in release.files.filter(FileType.status.has(identifier = 'movie')).all():
                        files.append(file.path)

                    # get subtitles for those files
                    subliminal.download_best_subtitles(files, languages = self.getLanguages(), providers = self.services)

    def searchSingle(self, group):
        if self.isDisabled(): return

        try:
            available_languages = sum(group['subtitle_language'].itervalues(), [])
            downloaded = []
            files = [toUnicode(x) for x in group['files']['movie']]
            log.debug('Searching for subtitles for: %s', files)

            for lang in self.getLanguages():
                if lang not in available_languages:
                    download = subliminal.download_best_subtitles(files, languages = [lang], providers = self.services)
                    for subtitle in download:
                        downloaded.extend(download[subtitle])

            for d_sub in downloaded:
                log.info('Found subtitle (%s): %s', (d_sub.language.alpha2, files))
                group['files']['subtitle'].append(sp(d_sub.path))
                group['before_rename'].append(sp(d_sub.path))
                group['subtitle_language'][sp(d_sub.path)] = [d_sub.language.alpha2]

            return True

        except:
            log.error('Failed searching for subtitle: %s', (traceback.format_exc()))

        return False

    def getLanguages(self):
        return splitString(self.conf('languages'))
