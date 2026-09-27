# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals

import pytest

import constants
import state
import tmdb_helper
from settings import SETTINGS


def test_library_now_playing_uses_plugin_metadata_and_normalised_title(monkeypatch):
    current_video = {
        'type': 'episode',
        'mediapath': 'plugin://plugin.video.elementum/play?tmdb_id=123&season=1&episode=2',
        'file': '',
        'tvshowid': constants.UNDEFINED,
        'showtitle': '[B]Example Show[/B]',
        'season': constants.UNDEFINED,
        'episode': constants.UNDEFINED,
        'label': 'Example Show S01E02',
    }
    lookups = []

    monkeypatch.setattr(state.api, 'get_now_playing',
                        lambda properties, retry: current_video.copy())

    def fake_get_tvshowid(title):
        lookups.append(title)
        if title == 'Example Show':
            return 77
        return constants.UNDEFINED

    monkeypatch.setattr(state.api, 'get_tvshowid', fake_get_tvshowid)
    monkeypatch.setattr(
        state.api,
        'get_episode_info',
        lambda tvshowid, season, episode: {
            'episodeid': 88,
            'tvshowid': tvshowid,
            'season': season,
            'episode': episode,
            'showtitle': 'Example Show',
        }
    )
    monkeypatch.setattr(
        state.UpNextState,
        '_get_tmdb_now_playing',
        staticmethod(lambda *args, **kwargs: pytest.fail('TMDb fallback should not run'))
    )

    result = state.UpNextState._get_library_now_playing({'item': {'showtitle': '[B]Example Show[/B]'}})

    assert result['tvshowid'] == 77
    assert result['episodeid'] == 88
    assert result['tmdb_id'] == '123'
    assert result['season'] == 1
    assert result['episode'] == 2
    assert lookups == ['[B]Example Show[/B]', 'Example Show']


def test_library_now_playing_passes_native_tmdb_id_to_fallback(monkeypatch):
    current_video = {
        'type': 'episode',
        'mediapath': 'plugin://plugin.video.elementum/play?tmdb_id=456&season=3&episode=4&player=elementum',
        'file': '',
        'tvshowid': constants.UNDEFINED,
        'showtitle': 'Elementum Show',
        'season': constants.UNDEFINED,
        'episode': constants.UNDEFINED,
    }
    captured = {}

    monkeypatch.setattr(state.api, 'get_now_playing',
                        lambda properties, retry: current_video.copy())
    monkeypatch.setattr(state.api, 'get_tvshowid',
                        lambda title: constants.UNDEFINED)

    def fake_tmdb_fallback(video, title, season, episode, addon_id):
        captured.update({
            'tmdb_id': video.get('tmdb_id'),
            'player': video.get('player'),
            'title': title,
            'season': season,
            'episode': episode,
            'addon_id': addon_id,
        })
        return {'source': 'tmdb-fallback'}

    monkeypatch.setattr(
        state.UpNextState,
        '_get_tmdb_now_playing',
        staticmethod(fake_tmdb_fallback)
    )

    result = state.UpNextState._get_library_now_playing({'item': {'showtitle': 'Elementum Show'}})

    assert result == {'source': 'tmdb-fallback'}
    assert captured == {
        'tmdb_id': '456',
        'player': 'elementum',
        'title': 'Elementum Show',
        'season': 3,
        'episode': 4,
        'addon_id': 'plugin.video.elementum',
    }


def test_tmdb_wrapper_and_fallback_skip_when_helper_unavailable(monkeypatch):
    monkeypatch.setattr(tmdb_helper, 'tmdb_helper_is_available',
                        lambda: False)
    monkeypatch.setattr(SETTINGS, 'import_tmdbhelper', True)

    with pytest.raises(RuntimeError):
        tmdb_helper.TMDb()

    result = state.UpNextState._get_tmdb_now_playing(
        {'tmdb_id': '999'},
        'Unavailable Helper Show',
        1,
        2,
        'plugin.video.elementum'
    )

    assert result is None
