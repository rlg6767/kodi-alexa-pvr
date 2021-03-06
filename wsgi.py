#!/usr/bin/python
import os
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

"""
The MIT License (MIT)

Copyright (c) 2015 Maker Musings && m0ngr31

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

# For a complete discussion, see http://forum.kodi.tv/showthread.php?tid=254502

import datetime
import json
import os.path
import random
import re
import string
import sys
import threading

# Load the kodi.py file from the same directory where this wsgi file is located
sys.path += [os.path.dirname(__file__)]
import kodi

# This utility function constructs the required JSON for a full Alexa Skills Kit response

RE_SHOW_WITH_PARAM = re.compile(r"(.*) \([^)]+\)$")

def sanitize_show(show_name):
  m = RE_SHOW_WITH_PARAM.match(show_name)
  if m:
    return m.group(1)
  return show_name

def build_alexa_response(speech = None, session_attrs = None, card = None, reprompt = None, end_session = True):
  return build_response(session_attrs, build_speechlet_response("", speech, "", end_session))


# Handle the CheckNewShows intent

def alexa_check_new_episodes(slots):
  print 'Checking if there are new shows to watch'
  sys.stdout.flush()
  # Responds to the question, "Are there any new shows to watch?"

  # Get the list of unwatched EPISODES from Kodi
  new_episodes = kodi.GetUnwatchedEpisodes()

  # Find out how many EPISODES were recently added and get the names of the SHOWS
  really_new_episodes = [x for x in new_episodes if x['dateadded'] >= datetime.datetime.today() - datetime.timedelta(5)]
  really_new_show_names = list(set([sanitize_show(x['show']) for x in really_new_episodes]))

  if len(really_new_episodes) == 0:
    answer = "There isn't anything new to watch."
  elif len(really_new_show_names) == 1:
    # Only one new show, so provide the number of episodes also.
    count = len(really_new_episodes)
    if count == 1:
      answer = "There is one new episide of %(show)s to watch." % {"show":really_new_show_names[0]}
    else:
      answer = "You have %(count)d new episides of %(show)s." % {'count':count, 'show':really_new_show_names[0]}
  elif len(really_new_show_names) == 2:
    random.shuffle(really_new_show_names)
    answer = "There are new episodes of %(show1)s and %(show2)s." % {'show1':really_new_show_names[0], 'show2':really_new_show_names[1]}
  elif len(really_new_show_names) > 2:
    show_sample = random.sample(really_new_show_names, 2)
    answer = "You have %(show1)s, %(show2)s, and more waiting to be watched." % {'show1':show_sample[0], 'show2':show_sample[1]}
  return build_alexa_response(answer)


# Handle the NewShowInquiry intent.

def alexa_new_show_inquiry(slots):
  heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

  print('Checking if there are new episodes to watch of %s' % (heard_show))
  sys.stdout.flush()

  shows = kodi.GetTvShows()
  if 'result' in shows and 'tvshows' in shows['result']:
    shows_array = shows['result']['tvshows']

    located = kodi.matchHeard(heard_show, shows_array)

    if located:
      episodes_result = kodi.GetUnwatchedEpisodesFromShow(located['tvshowid'])

      if not 'episodes' in episodes_result['result']:
        num_of_unwatched = 0

      else:
        num_of_unwatched = len(episodes_result['result']['episodes'])

      if num_of_unwatched > 0:
        if num_of_unwatched == 1:
          return build_alexa_response("There is one unseen episode of %(real_show)s." % {'real_show': heard_show})
        else:
          return build_alexa_response("There are %(num)d episodes of  %(real_show)s." % {'real_show': heard_show, 'num': num_of_unwatched})

      else:
        return build_alexa_response("There are no unseen episodes of %(real_show)s." % {'real_show': heard_show})
    else:
      return build_alexa_response('Could not find %s' % (heard_show))
  else:
    return build_alexa_response('Error parsing results.')

# Handle the CurrentPlayItemInquiry intent.

def alexa_current_playitem_inquiry(slots):
  print('Trying to get info about current player item')
  sys.stdout.flush()

  speech_output = 'The current'
  speech_output_append = 'ly playing item is unknown'

  try:
    curitem = kodi.GetActivePlayItem()
  except:
    speech_output = 'There is nothing current'
    speech_output_append = 'ly playing'
  else:
    if curitem is not None:
      if curitem['type'] == 'episode':
        # is a tv show
        speech_output += ' TV show is'
        speech_output_append = ' unknown'
        if curitem['showtitle']:
          speech_output += ' %s,' % (curitem['showtitle'])
          speech_output_append = ''
        if curitem['season']:
          speech_output += ' season %s,' % (curitem['season'])
          speech_output_append = ''
        if curitem['episode']:
          speech_output += ' episode %s,' % (curitem['episode'])
          speech_output_append = ''
        if curitem['title']:
          speech_output += ' %s' % (curitem['title'])
          speech_output_append = ''
      elif curitem['type'] == 'song' or curitem['type'] == 'musicvideo':
        # is a song (music video or audio)
        speech_output += ' song is'
        speech_output_append = ' unknown'
        if curitem['title']:
          speech_output += ' %s,' % (curitem['title'])
          speech_output_append = ''
        if curitem['artist']:
          speech_output += ' by %s,' % (curitem['artist'][0])
          speech_output_append = ''
        if curitem['album']:
          speech_output += ' on the album %s' % (curitem['album'])
          speech_output_append = ''
      elif curitem['type'] == 'movie':
        # is a video
        speech_output += ' movie is'
        speech_output_append = ' unknown'
        if curitem['title']:
          speech_output += ' %s' % (curitem['title'])
          speech_output_append = ''

    return build_alexa_response('%s%s.' % (speech_output, speech_output_append))

# Pause Kodi
def alexa_play_pause(slots):
  print('Playing or Pausing')
  sys.stdout.flush()

  kodi.PlayPause()
  answer = ""
  return build_alexa_response(answer)

# Stop Playback
def alexa_stop(slots):
  print('Stopping Playback')
  sys.stdout.flush()

  kodi.Stop()
  answer = "Playback Stopped"
  return build_alexa_response(answer)

# Shuffle all music by an artist
def alexa_play_artist(slots):
  heard_artist = str(slots['Artist']['value']).lower().translate(None, string.punctuation)
  
  print('Trying to play music by %s' % (heard_artist))
  sys.stdout.flush()

  artists = kodi.GetMusicArtists()
  if 'result' in artists and 'artists' in artists['result']:
    artists_list = artists['result']['artists']
    located = kodi.matchHeard(heard_artist, artists_list, 'artist')

    if located:
      songs_result = kodi.GetArtistSongs(located['artistid'])
      songs = songs_result['result']['songs']

      kodi.Stop()
      kodi.ClearPlaylist()

      songs_array = []

      for song in songs:
        songs_array.append(song['songid'])

      kodi.AddSongsToPlaylist(songs_array)

      kodi.StartPlaylist()
      return build_alexa_response('Playing %s' % (heard_artist))
    else:
      return build_alexa_response('Could not find %s' % (heard_artist))
  else:
    return build_alexa_response('Could not find %s' % (heard_artist))

# Shuffle all recently added songs
def alexa_play_recently_added_songs(slots):
  print('Trying to play recently added songs')
  sys.stdout.flush()

  songs_result = kodi.GetRecentlyAddedSongs()
  if songs_result:
    songs = songs_result['result']['songs']

    kodi.Stop()
    kodi.ClearPlaylist()

    songs_array = []

    for song in songs:
      songs_array.append(song['songid'])

    kodi.AddSongsToPlaylist(songs_array)

    kodi.StartPlaylist()
    return build_alexa_response('Playing recently added songs')
  return build_alexa_response('No recently added songs found')

def alexa_play_playlist(slots):
  heard_playlist = str(slots['Playlist']['value']).lower().translate(None, string.punctuation)

  print('Trying to play playlist "%s"' % (heard_playlist))
  sys.stdout.flush()

  playlists = kodi.GetMusicPlaylists()
  if 'result' in playlists and 'files' in playlists['result']:
    playlists_list = playlists['result']['files']
    located = kodi.matchHeard(heard_playlist, playlists_list, 'label')

    if located:
      print 'Playing playlist "%s"' % (located['file'])
      sys.stdout.flush()
      kodi.StartPlaylist(located['file'])
      return build_alexa_response('Playing playlist %s' % (heard_playlist))
    else:
      return build_alexa_response('Could not find %s' % (heard_playlist))
  else:
    return build_alexa_response('Error parsing results.')

def alexa_party_play(slots):
  songs = kodi.GetAllSongs()

  if 'result' in songs and 'songs' in songs['result']:
    kodi.Stop()
    kodi.ClearPlaylist()

    songs_array = []

    for song in songs['result']['songs']:
      songs_array.append(song['songid'])

    random.shuffle(songs_array)
    print songs_array

    kodi.AddSongsToPlaylist(songs_array)
    kodi.StartPlaylist()
    return build_alexa_response('Starting Party play')
  else:
    return build_alexa_response('Error parsing results.')

def alexa_start_over(slots):
  print('Starting current item over')
  sys.stdout.flush()

  kodi.PlayStartOver()
  return build_alexa_response('Starting over')

def alexa_skip(slots):
  print('Skipping')
  sys.stdout.flush()

  kodi.PlaySkip()
  return build_alexa_response('Skipping item')

def alexa_pageup(slots):
  print('Going PageUp')
  sys.stdout.flush()

  kodi.PageUp()
  return build_alexa_response('')

def alexa_pagedown(slots):
  print('Going PageDown')
  sys.stdout.flush()

  kodi.PageDown()
  return build_alexa_response('')

def alexa_fullscreen(slots):
  print('Toggling fullscreen')
  sys.stdout.flush()

  kodi.ToggleFullscreen()
  answer = ""
  return build_alexa_response(answer)

def alexa_mute(slots):
  print('Muting or unmuting')
  sys.stdout.flush()

  kodi.ToggleMute()
  answer = ""
  return build_alexa_response(answer)

def alexa_subtitles_on(slots):
  print('Enabling subtitles')
  sys.stdout.flush()

  kodi.SubtitlesOn()
  answer = kodi.GetCurrentSubtitles()
  return build_alexa_response(answer)

def alexa_subtitles_off(slots):
  print('Disabling subtitles')
  sys.stdout.flush()

  kodi.SubtitlesOff()
  answer = kodi.GetCurrentSubtitles()
  return build_alexa_response(answer)

def alexa_subtitles_next(slots):
  print('Switching to next subtitles')
  sys.stdout.flush()

  kodi.SubtitlesNext()
  answer = kodi.GetCurrentSubtitles()
  return build_alexa_response(answer)

def alexa_subtitles_previous(slots):
  print('Switching to previous subtitles')
  sys.stdout.flush()

  kodi.SubtitlesPrevious()
  answer = kodi.GetCurrentSubtitles()
  return build_alexa_response(answer)

def alexa_audiostream_next(slots):
  print('Switching to next audio stream')
  sys.stdout.flush()

  kodi.AudioStreamNext()
  answer = kodi.GetCurrentAudioStream()
  return build_alexa_response(answer)

def alexa_audiostream_previous(slots):
  print('Switching to previous audio stream')
  sys.stdout.flush()

  kodi.AudioStreamPrevious()
  answer = kodi.GetCurrentAudioStream()
  return build_alexa_response(answer)

def alexa_context_menu(slots):
  print('Opening context menu')
  sys.stdout.flush()

  kodi.Menu()
  return build_alexa_response('Opening menu')

def alexa_go_home(slots):
  print('Returning to home')
  sys.stdout.flush()

  kodi.Home()
  return build_alexa_response('Going home')

def alexa_select(slots):
  print('Selecting')
  sys.stdout.flush()

  kodi.Select()
  return build_alexa_response('')

def alexa_left(slots):
  print('Going left')
  sys.stdout.flush()

  kodi.Left()
  return build_alexa_response('')

def alexa_right(slots):
  print('Going right')
  sys.stdout.flush()

  kodi.Right()
  return build_alexa_response('')

def alexa_up(slots):
  print('Going up')
  sys.stdout.flush()

  kodi.Up()
  return build_alexa_response('')

def alexa_down(slots):
  print('Going down')
  sys.stdout.flush()

  kodi.Down()
  return build_alexa_response('')

def alexa_back(slots):
  print('Going back')
  sys.stdout.flush()

  kodi.Back()
  return build_alexa_response('')

def alexa_prev(slots):
  print('Playing previous item')
  sys.stdout.flush()

  kodi.PlayPrev()
  return build_alexa_response('Playing previous item')

# Handle the Hibernate intent.

def alexa_hibernate(slots):
  print('Trying to hibernate system')
  sys.stdout.flush()

  kodi.SystemHibernate()
  answer = "Hibernating system"
  return build_alexa_response(answer)

# Handle the Reboot intent.

def alexa_reboot(slots):
  print('Trying to reboot system')
  sys.stdout.flush()

  kodi.SystemReboot()
  answer = "Rebooting system"
  return build_alexa_response(answer)

# Handle the Shutdown intent.

def alexa_shutdown(slots):
  print('Trying to shut down system')
  sys.stdout.flush()

  kodi.SystemShutdown()
  answer = "Shutting down system"
  return build_alexa_response(answer)

# Handle the Suspend intent.

def alexa_suspend(slots):
  print('Trying to suspend system')
  sys.stdout.flush()

  kodi.SystemSuspend()
  answer = "Suspending system"
  return build_alexa_response(answer)

# Handle the EjectMedia intent.

def alexa_ejectmedia(slots):
  print('Trying to eject disc')
  sys.stdout.flush()

  kodi.SystemEjectMedia()
  answer = "Ejecting"
  return build_alexa_response(answer)

def alexa_clean_video(slots):
  print('Cleaning video library')
  sys.stdout.flush()

  kodi.UpdateVideo()

  #Use threading to solve the call from returing too late
  c = threading.Thread(target=kodi.CleanVideo)
  c.daemon = True
  c.start()

  #Calling this because for some reason it won't fire until the next command happens?
  kodi.Home()

  return build_alexa_response('Cleaning and updating video library')

def alexa_update_video(slots):
  print('Updating video library')
  sys.stdout.flush()

  kodi.UpdateVideo()

  return build_alexa_response('Updating video library')

def alexa_clean_audio(slots):
  print('Cleaning audio library')
  sys.stdout.flush()

  kodi.UpdateMusic()

  #Use threading to solve the call from returing too late
  c = threading.Thread(target=kodi.CleanMusic)
  c.daemon = True
  c.start()

  #Calling this because for some reason it won't fire until the next command happens?
  kodi.Home()

  return build_alexa_response('Cleaning and updating audio library')

def alexa_update_audio(slots):
  print('Updating audio library')
  sys.stdout.flush()

  kodi.UpdateMusic()

  return build_alexa_response('Updating audio library')

def alexa_do_search(slots):
  heard_search = ''

  if 'value' in slots['Movie']:
    heard_search = str(slots['Movie']['value']).lower().translate(None, string.punctuation)
  elif 'value' in slots['Show']:
    heard_search = str(slots['Show']['value']).lower().translate(None, string.punctuation)
  elif 'value' in slots['Artist']:
    heard_search = str(slots['Artist']['value']).lower().translate(None, string.punctuation)

  if(len(heard_search) > 0):
    kodi.Home()
    kodi.CallKodiSearch(heard_search)

    return build_alexa_response('Searching for %s' % (heard_search))
  else:
    return build_alexa_response("Couldn't find anything matching that phrase")

def alexa_pick_random_movie(slots):
  print('Trying to play a random movie')
  sys.stdout.flush()

  movies_response = kodi.GetUnwatchedMovies()
  if 'result' in movies_response and 'movies' in movies_response['result']:
    movies = movies_response['result']['movies']
    random_movie = random.choice(movies)

    kodi.ClearVideoPlaylist()
    kodi.PrepMoviePlaylist(random_movie['movieid'])
    kodi.StartVideoPlaylist()

    return build_alexa_response('Playing %s' % (random_movie['label']))
  else:
    return build_alexa_response('Error parsing results.')

def alexa_play_movie(slots):
  heard_movie = str(slots['Movie']['value']).lower().translate(None, string.punctuation)

  print('Trying to play the movie %s' % (heard_movie))
  sys.stdout.flush()

  movies_response = kodi.GetMovies()
  if 'result' in movies_response and 'movies' in movies_response['result']:
    movies = movies_response['result']['movies']

    located = kodi.matchHeard(heard_movie, movies)

    if located:
      kodi.ClearVideoPlaylist()
      kodi.PrepMoviePlaylist(located['movieid'])
      kodi.StartVideoPlaylist()

      return build_alexa_response('Playing %s' % (heard_movie))
    else:
      return build_alexa_response('Could not find a movie called %s' % (heard_movie))
  else:
    return build_alexa_response('Error parsing results.')

def alexa_pick_random_episode(slots):
  heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

  print('Trying to play a random episode of %s' % (heard_show))
  sys.stdout.flush()

  shows = kodi.GetTvShows()
  if 'result' in shows and 'tvshows' in shows['result']:
    shows_array = shows['result']['tvshows']

    located = kodi.matchHeard(heard_show, shows_array)

    if located:
      episodes_result = kodi.GetUnwatchedEpisodesFromShow(located['tvshowid'])

      if not 'episodes' in episodes_result['result']:
        episodes_result = kodi.GetEpisodesFromShow(located['tvshowid'])

      episodes_array = []

      for episode in episodes_result['result']['episodes']:
        episodes_array.append(episode['episodeid'])

      kodi.ClearVideoPlaylist()
      kodi.PrepEpisodePlayList(random.choice(episodes_array))

      kodi.StartVideoPlaylist()

      return build_alexa_response('Playing a random episode of %s' % (heard_show))
    else:
      return build_alexa_response('Could not find %s' % (heard_show))
  else:
    return build_alexa_response('Error parsing results.')


def alexa_play_episode(slots):
  heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

  print('Trying to play a specific episode of %s' % (heard_show))
  sys.stdout.flush()

  shows = kodi.GetTvShows()
  if 'result' in shows and 'tvshows' in shows['result']:
    shows_array = shows['result']['tvshows']

    heard_season = slots['Season']['value']
    heard_episode = slots['Episode']['value']

    located = kodi.matchHeard(heard_show, shows_array)

    if located:
      episode_result = kodi.GetSpecificEpisode(located['tvshowid'], heard_season, heard_episode)

      if episode_result:
        kodi.ClearVideoPlaylist()
        kodi.PrepEpisodePlayList(episode_result)
        kodi.StartVideoPlaylist()

        return build_alexa_response('Playing season %s episode %s of %s' % (heard_season, heard_episode, heard_show))

      else:
        return build_alexa_response('Could not find season %s episode %s of %s' % (heard_season, heard_episode, heard_show))
    else:
      return build_alexa_response('Could not find %s' % (heard_show))
  else:
    return build_alexa_response('Error parsing results.')


def alexa_play_next_episode(slots):
  heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

  print('Trying to play the next episode of %s' % (heard_show))
  sys.stdout.flush()

  shows = kodi.GetTvShows()
  if 'result' in shows and 'tvshows' in shows['result']:
    shows_array = shows['result']['tvshows']

    located = kodi.matchHeard(heard_show, shows_array)

    if located:
      next_episode = kodi.GetNextUnwatchedEpisode(located['tvshowid'])

      if next_episode:
        kodi.ClearVideoPlaylist()
        kodi.PrepEpisodePlayList(next_episode)

        kodi.StartVideoPlaylist()
        return build_alexa_response('Playing next episode of %s' % (heard_show))
      else:
        return build_alexa_response('No new episodes for %s' % (heard_show))
    else:
      return build_alexa_response('Could not find %s' % (heard_show))
  else:
    return build_alexa_response('Error parsing results.')


def alexa_play_newest_episode(slots):
  heard_show =  str(slots['Show']['value']).lower().translate(None, string.punctuation)

  print('Trying to play the newest episode of %s' % (heard_show))
  sys.stdout.flush()

  shows = kodi.GetTvShows()
  if 'result' in shows and 'tvshows' in shows['result']:
    shows_array = shows['result']['tvshows']

    located = kodi.matchHeard(heard_show, shows_array)

    if located:
      episode_result = kodi.GetNewestEpisodeFromShow(located['tvshowid'])

      if episode_result:
        kodi.ClearVideoPlaylist()
        kodi.PrepEpisodePlayList(episode_result)
        kodi.StartVideoPlaylist()

        return build_alexa_response('Playing latest episode of %s' % (heard_show))

      else:
        return build_alexa_response('Could not find newest episode of %s' % (heard_show))
    else:
      return build_alexa_response('Could not find %s' % (heard_show))
  else:
    return build_alexa_response('Error parsing results.')


def alexa_continue_show(slots):
  print('Trying to continue watching the last show')
  sys.stdout.flush()

  last_show_obj = kodi.GetLastWatchedShow()

  try:
    last_show_id = last_show_obj['result']['episodes'][0]['tvshowid']
    next_episode = kodi.GetNextUnwatchedEpisode(last_show_id)

    if next_episode:
      kodi.ClearVideoPlaylist()
      kodi.PrepEpisodePlayList(next_episode)

      kodi.StartVideoPlaylist()
      return build_alexa_response('Playing next episode')
    else:
      return build_alexa_response('No new episodes')

  except:
    return build_alexa_response('Could not continue show')

# Handle the WhatNewShows intent.

def alexa_what_new_episodes(slots):
  print('Trying to get a list of unwatched shows')
  sys.stdout.flush()

  # Lists the shows that have had new episodes added to Kodi in the last 5 days

  # Get the list of unwatched EPISODES from Kodi
  new_episodes = kodi.GetUnwatchedEpisodes()

  # Find out how many EPISODES were recently added and get the names of the SHOWS
  really_new_episodes = [x for x in new_episodes if x['dateadded'] >= datetime.datetime.today() - datetime.timedelta(5)]
  really_new_show_names = list(set([sanitize_show(x['show']) for x in really_new_episodes]))
  num_shows = len(really_new_show_names)

  if num_shows == 0:
    # There's been nothing added to Kodi recently
    answers = [
      "You don't have any new shows to watch.",
      "There are no new shows to watch.",
    ]
    answer = random.choice(answers)
    if random.random() < 0.25:
      comments = [
        " Maybe you should go to the movies.",
        " Maybe you'd like to read a book.",
        " Time to go for a bike ride?",
        " You probably have chores to do anyway.",
      ]
      answer += random.choice(comments)
  elif len(really_new_show_names) == 1:
    # There's only one new show, so provide information about the number of episodes, too.
    count = len(really_new_episodes)
    if count == 1:
      answers = [
        "There is a single new episode of %(show)s." % {'show':really_new_show_names[0]},
        "There is one new episode of %(show)s." % {'show':really_new_show_names[0]},
      ]
    elif count == 2:
      answers = [
        "There are a couple new episodes of %(show)s" % {'show':really_new_show_names[0]},
        "There are two new episodes of %(show)s" % {'show':really_new_show_names[0]},
      ]
    elif count >= 5:
      answers = [
        "There are lots and lots of new episodes of %(show)s" % {'show':really_new_show_names[0]},
        "There are %(count)d new episodes of %(show)s" % {"count":count, "show":really_new_show_names[0]},
      ]
    else:
      answers = [
        "You have a few new episodes of %(show)s" % {'show':really_new_show_names[0]},
        "There are %(count)d new episodes of %(show)s" % {"count":count, "show":really_new_show_names[0]},
      ]
    answer = random.choice(answers)
  else:
    # More than one new show has new episodes ready
    random.shuffle(really_new_show_names)
    show_list = really_new_show_names[0]
    for one_show in really_new_show_names[1:-1]:
      show_list += ", " + one_show
    show_list += ", and " + really_new_show_names[-1]
    answer = "There are new episodes of %(show_list)s." % {"show_list":show_list}
  return build_alexa_response(answer)


PVR_CHANNELS_BY_LABEL = None
PVR_CHANNELS_BY_ID = None
PVR_BROADCASTS = None
CHANNEL_FIXES = [
  ['BBC One Yk & Li','bbc 1 yorkshire and '],
  ['ITV2+1','itv 2 plus 1'],
  ['BBC One S West','bbc 1 south west'],
  ['Film4+1','film 4 plus 1'],
  ['ITV4+1','itv 4 plus 1'],
  ['Channel 5+1','channel 5 plus 1'],
  ['5STAR','5 star'],
  ['BBC One HD','bbc 1 hd'],
  ['My5','my 5'],
  ['True Ent+1','true end plus 1'],
  ['Channel 4+1','channel 4 plus 1'],
  ['BBC One S East','bbc 1 south east'],
  ['BBC One Wales','bbc 1 wales'],
  ['BBC One NI HD','bbc 1 northern ireland hd'],
  ['5 USA+1','5 usa plus 1'],
  ['Film4','film 4'],
  ['Fashion One','fashion 1'],
  ['BBC One East W','bbc 1 east'],
  ['BBC One Oxford','bbc 1 oxford'],
  ['ITV3+1','itv 3 plus 1'],
  ['Channel 5HD','channel 5 hd'],
  ['BBC One East E','bbc 1 east'],
  ['BBC Two Wales','bbc 2 wales'],
  ['movies4men','movies for men'],
  ['FRANCE Eng','france english'],
  ['BBC One South','bbc 1 south'],
  ['More4','more 4'],
  ['More4 +1','more 4 plus 1'],
  ['POP+1','pop plus 1'],
  ['E4','e 4'],
  ['TrueChrstms+1','true christmas plus 1'],
  ['BBC Two HD','bbc 2 hd'],
  ['BBC One ScotHD','bbc 1 scotland hd'],
  ['BBC One West','bbc 1 west'],
  ['Pick+1','pick plus 1'],
  ['YourTV','your tv'],
  ['CBS Reality+1','cbs reality plus 1'],
  ['ITV4','itv 4'],
  ['4seven','4 7'],
  ['ITV3','itv 3'],
  ['ITV2','itv 2'],
  ['Travel Ch+1','travel channel plus 1'],
  ['Channel 4', 'channel 4'],
  ['Channel 4 +1', 'channel 4 plus 1'],
  ['E4+1','e 4 plus 1'],
  ['BBC One E Mid','bbc 1 east midlands'],
  ['S4C HD','s 4 c hd'],
  ['BBC One Lon','bbc 1'],
  ['BBC Two Scot','bbc 2 scotland'],
  ['Challenge+1','challenge plus 1'],
  ['BBC One NI','bbc 1 northern ireland'],
  ['BBC One NE & C','bbc 1 northern ireland and counties'],
  ['BBC One Wal HD','bbc 1 wales hd'],
  ['BBC One Yorks','bbc 1 yorkshire'],
  ['ITVBe','itv be'],
  ['ITVBe+1','itv be plus 1'],
  ['BBC Four','bbc 4'],
  ['BBC One Scot','bbc 1 scotland'],
  ['BBC Two Eng','bbc 2'],
  ['True Crime+1','true crime plus 1'],
  ['5STAR+1','5 star plus 1'],
  ['mov4men+1','movies for men plus one'],
  ['horror ch+1','horro channel plus 1'],
  ['BBC One N West','bbc 1 north west'],
  ['BBC RB1','bbc rb 1'],
  ['BBC One W Mid','bbc 1 west midlands'],
  ['BBC Four HD','bbc 4 hd'],
  ['Food Netwrk+1','food network plus 1'],
  ['BBC One CI','bbc 1 c i'],
  ['BBC Two NI','bbc 2 northern ireland']
]

PVR_SEARCH_CHANNELS = [
  'bbc 1 hd',
  'bbc 2 hd',
  'bbc 4 hd',
  'itv hd',
  'itv plus 1',
  'itv 2',
  'itv 2 plus 1',
  'itv 3',
  'itv 3 plus 1',
  'itv 4',
  'itv 4 plus 1',
  'itv be',
  'itv be plus 1',
  'channel 4 hd',
  'channel 4 plus 1',
  'my5',
  'channel 5 hd',
  'channel 5 plus 1',
  'e 4',
  'e 4 plus 1',
  'more 4',
  'more 4 plus 1',
  'film 4',
  'film 4 plus 1'
  ]


def fix_channel_label(label):
  for fix in CHANNEL_FIXES:
    if label.lower() == fix[0].lower():
      return fix[1].lower()
  return label.lower()



def alexa_watch_pvr_channel(slots):
  print('raw slots #')
  print(slots)
  heard_pvr_channel = str(slots['Channel']['value'])

  print('Trying to play the PVR channel %s' % (heard_pvr_channel))
  sys.stdout.flush()

  global PVR_CHANNELS_BY_LABEL
  if not PVR_CHANNELS_BY_LABEL:
    pvr_channels_response = kodi.GetPVRChannels()
    if 'result' in pvr_channels_response and 'channels' in pvr_channels_response['result']:
      PVR_CHANNELS_BY_LABEL = {fix_channel_label(channel['label']): channel['channelid'] for channel in pvr_channels_response['result']['channels']}
    else:
      return build_alexa_response('Error parsing results.')

  located = process.extract(heard_pvr_channel, PVR_CHANNELS_BY_LABEL.keys(), scorer=fuzz.QRatio, limit=1)
  channel, score = located[0]

  if score > 75:
    kodi.WatchPVRChannel(PVR_CHANNELS_BY_LABEL[channel.lower()])
    #kodi.ClearVideoPlaylist()
    #kodi.PrepMoviePlaylist(located['movieid'])
    #kodi.StartVideoPlaylist()

    return build_alexa_response('Playing PVR channel %s' % (channel))
  else:
    return build_alexa_response('Could not find a PVR channel called %s' % (heard_pvr_channel))


def alexa_watch_pvr_broadcast(slots):
  print(slots)
  sys.stdout.flush()
  #heard_pvr_broadcast = str(slots['Broadcasts']['value']).lower().translate(None, string.punctuation)
  heard_pvr_broadcast = str(slots['Broadcast']['value'])

  print('Trying to play the PVR broadcast %s' % (heard_pvr_broadcast))
  sys.stdout.flush()

  global PVR_CHANNELS_BY_ID
  if not PVR_CHANNELS_BY_ID:
    pvr_channels_response = kodi.GetPVRChannels()
    if 'result' in pvr_channels_response and 'channels' in pvr_channels_response['result']:
      PVR_CHANNELS_BY_ID = {channel['channelid'] : fix_channel_label(channel['label']) for channel in pvr_channels_response['result']['channels']}
    else:
      return build_alexa_response('Error parsing results.')

  global PVR_BROADCASTS
  if not PVR_BROADCASTS:
    PVR_BROADCASTS = {}
    for id, channel in PVR_CHANNELS_BY_ID.iteritems():
      try:
        PVR_SEARCH_CHANNELS.index(channel)
        pvr_broadcasts_response = kodi.GetPVRBroadcasts(id)

        if 'result' in pvr_broadcasts_response:
          if 'broadcasts' in pvr_broadcasts_response['result']:
            pvr_broadcasts = pvr_broadcasts_response['result']['broadcasts']
            PVR_BROADCASTS[id] = pvr_broadcasts
        else:
          return build_alexa_response('Error parsing broadcast results.')
      except ValueError:
        None

  #print(PVR_BROADCASTS)
  candidate_broadcasts = []
  for channelid, broadcasts in PVR_BROADCASTS.items():
    response = process.extract(heard_pvr_broadcast, [broadcast['label'] for broadcast in broadcasts], scorer=fuzz.QRatio, limit=1)

    if len(response) != 0 and response[0][1] > 75:
      for broadcast in broadcasts:
        if broadcast['label'] == response[0][0]:
          candidate_broadcasts.append({"channel":channelid, "broadcast":broadcast})

  best_candidate = None

  if len(candidate_broadcasts) > 0:
    #print(candidate_broadcasts)
    for candidate in candidate_broadcasts:
      # all dates in the response appear to be UTC
      candidate_endtime = datetime.datetime.strptime(candidate['broadcast']['endtime'], "%Y-%m-%d %H:%M:%S",)
      if candidate_endtime > datetime.datetime.utcnow() and (best_candidate is None or candidate_endtime < best_candidate_endtime):
        best_candidate = candidate
        best_candidate_endtime = candidate_endtime

  if best_candidate:
    #print(best_candidate)
    kodi.WatchPVRChannel(best_candidate['channel'])
    # kodi.ClearVideoPlaylist()
    # kodi.PrepMoviePlaylist(located['movieid'])
    # kodi.StartVideoPlaylist()

    return build_alexa_response('Playing %s on %s' % (best_candidate['broadcast']['label'], PVR_CHANNELS_BY_ID[best_candidate['channel']]))
  else:
    return build_alexa_response('Could not find a PVR broadcast called %s' % (heard_pvr_broadcast))


# What should the Echo say when you just open your app instead of invoking an intent?

def prepare_help_message():
  help = "You can ask me whether there are any new shows, to play a movie, tv show, or artist, or control playback of media."
  return build_alexa_response(help)


# This maps the Intent names to the functions that provide the corresponding Alexa response.

INTENTS = [
  ['CheckNewShows', alexa_check_new_episodes],
  ['NewShowInquiry', alexa_new_show_inquiry],
  ['CurrentPlayItemInquiry', alexa_current_playitem_inquiry],
  ['WhatNewShows', alexa_what_new_episodes],
  ['PlayPause', alexa_play_pause],
  ['Stop', alexa_stop],
  ['ListenToArtist', alexa_play_artist],
  ['ListenToPlaylist', alexa_play_playlist],
  ['ListenToPlaylistRecent', alexa_play_recently_added_songs],
  ['Skip', alexa_skip],
  ['Prev', alexa_prev],
  ['StartOver', alexa_start_over],
  ['PlayRandomEpisode', alexa_pick_random_episode],
  ['PlayRandomMovie', alexa_pick_random_movie],
  ['PlayMovie', alexa_play_movie],
  ['Home', alexa_go_home],
  ['Back', alexa_back],
  ['Up', alexa_up],
  ['Down', alexa_down],
  ['Right', alexa_right],
  ['Left', alexa_left],
  ['Select', alexa_select],
  ['Menu', alexa_context_menu],
  ['PageUp', alexa_pageup],
  ['PageDown', alexa_pagedown],
  ['Fullscreen', alexa_fullscreen],
  ['Mute', alexa_mute],
  ['SubtitlesOn', alexa_subtitles_on],
  ['SubtitlesOff', alexa_subtitles_off],
  ['SubtitlesNext', alexa_subtitles_next],
  ['SubtitlesPrevious', alexa_subtitles_previous],
  ['AudioStreamNext', alexa_audiostream_next],
  ['AudioStreamPrevious', alexa_audiostream_previous],
  ['PlayEpisode', alexa_play_episode],
  ['PlayNextEpisode', alexa_play_next_episode],
  ['ContinueShow', alexa_continue_show],
  ['CleanVideo', alexa_clean_video],
  ['UpdateVideo', alexa_update_video],
  ['CleanAudio', alexa_clean_audio],
  ['UpdateAudio', alexa_update_audio],
  ['PlayLatestEpisode', alexa_play_newest_episode],
  ['PartyMode', alexa_party_play],
  ['DoSearch', alexa_do_search],
  ['Hibernate', alexa_hibernate],
  ['Reboot', alexa_reboot],
  ['Shutdown', alexa_shutdown],
  ['Suspend', alexa_suspend],
  ['EjectMedia', alexa_ejectmedia],
  ['WatchPVRChannel', alexa_watch_pvr_channel],
  ['WatchPVRBroadcast', alexa_watch_pvr_broadcast]
]

def do_alexa(environ, start_response):
  # Alexa requests come as POST messages with a request body
  try:
    length = int(environ.get('CONTENT_LENGTH', '0'))
  except ValueError:
    length = 0

  if length > 0:
    # Get the request body and parse out the Alexa JSON request
    body = environ['wsgi.input'].read(length)
    alexa_msg = json.loads(body)
    alexa_request = alexa_msg['request']

    if alexa_request['type'] == 'LaunchRequest':
      # This is the type when you just say "Open <app>"
      response = prepare_help_message()

    elif alexa_request['type'] == 'IntentRequest':
      # Get the intent being invoked and any slot values sent with it
      intent_name = alexa_request['intent']['name']
      intent_slots = alexa_request['intent'].get('slots', {})
      response = None

      print('Requested intent: %s' % (intent_name))
      sys.stdout.flush()

      # Run the function associated with the intent
      for one_intent in INTENTS:
        if intent_name == one_intent[0]:
          response = one_intent[1](intent_slots)
          break
      if not response:
        # This should not happen if your Intent Schema and your INTENTS list above are in sync.
        response = prepare_help_message()
    else:
      response = build_alexa_response("I received an unexpected request type.")
    start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(json.dumps(response))))])
    return [json.dumps(response)]
  else:
    # This should never happen with a real Echo request but could happen
    # if your URL is accessed by a browser or otherwise.
    start_response('502 No content', [])
    return ['']

# Map the URL to the WSGI function that should handle it.

HANDLERS = [
  ['/', do_alexa],
  ['', do_alexa],
]

# The main entry point for lambda
def lambda_handler(event, context):
  print("event.session.application.applicationId=" + event['session']['application']['applicationId'])

  kodi.SetupEnvVars()

  if event['session']['new']:
    on_session_started({'requestId': event['request']['requestId']}, event['session'])

  if event['request']['type'] == "LaunchRequest":
    return prepare_help_message()
  elif event['request']['type'] == "IntentRequest":
    return on_intent(event['request'], event['session'])
  else:
    return build_alexa_response("I received an unexpected request type.")

def on_session_started(session_started_request, session):
  print("on_session_started requestId=" + session_started_request['requestId'] + ", sessionId=" + session['sessionId'])

def on_intent(intent_request, session):
  print("on_intent requestId=" + intent_request['requestId'] + ", sessionId=" + session['sessionId'])

  intent = intent_request['intent']
  intent_name = intent_request['intent']['name']
  intent_slots = intent_request['intent'].get('slots',{})

  # Dispatch to your skill's intent handlers
  response = None

  print('Requested intent: %s' % (intent_name))
  sys.stdout.flush()

  # Run the function associated with the intent
  for one_intent in INTENTS:
    if intent_name == one_intent[0]:
      return one_intent[1](intent_slots)
      break
  if not response:
    return prepare_help_message()


# The main entry point for WSGI scripts
def application(environ, start_response):
  # Execute the handler that matches the URL
  for h in HANDLERS:
    if environ['PATH_INFO'] == h[0]:
      output = h[1](environ, start_response)
      return output

  # If we don't have a handler for the URL, return a 404 error
  # page with diagnostic info. The details should be left blank
  # in a real production environment.

  details = ''
  if False:  # Change to False for productioN!
    for k in sorted(environ.keys()):
      details += '%s = %s<br/>\n' % (k, environ[k])
  output = """<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>404 Not Found</title>
</head><body>
<h1>Not Found</h1>
<p>The requested URL %(url)s was not found on this server.</p>
<hr/>
%(details)s
<hr/>
<address>%(address)s</address>
</body></html>
""" % {'url':environ['PATH_INFO'], 'address':environ['SERVER_SIGNATURE'], 'details':details}
  start_response('404 Not Found', [('Content-type', 'text/html')])
  return [output]

def build_response(session_attributes, speechlet_response):
  return {
    'version': '1.0',
    'sessionAttributes': session_attributes,
    'response': speechlet_response
  }

def build_speechlet_response(title, output, reprompt_text, should_end_session):
  return {
    'outputSpeech': {
      'type': 'PlainText',
      'text': output
    },
    'card': {
      'type': 'Simple',
      'title': 'SessionSpeechlet - ' + title,
      'content': 'SessionSpeechlet - ' + output
    },
    'reprompt': {
      'outputSpeech': {
        'type': 'PlainText',
        'text': reprompt_text
      }
    },
    'shouldEndSession': should_end_session
  }
