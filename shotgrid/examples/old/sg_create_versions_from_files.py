#!/usr/bin/env python
# encoding: utf-8
"""
sg_create_versions_from_files.py

Create Versions in Shotgun from a folder of local files

• Create a new version with the name based on the filename
• Transcode the file and generate thumbnails and web-playable media

Note: project ID is hardcoded
Requires ffmpeg to be installed in same folder

"""

import sys, os, json, datetime, shutil, glob, subprocess, math, time, tempfile, re, fnmatch
from shotgun_api3.shotgun import Shotgun

FFMPEG_BINARY = '"'+os.path.join(os.path.dirname(__file__), "ffmpeg")+'"'
project_id = 99

movieTypes = [
    "mov",
    "mp4",
    "avi"
]
imageTypes = [
    "[Jj][Pp][Gg]",
    "[Jj][Pp][Ee][Gg]",
    "[Tt][Ii][Ff]",
    "[Tt][Ii][Ff][Ff]",
    "[Ee][Xx][Rr]",
    "[Dd][Pp][Xx]",
    "[Pp][Nn][Gg]",
    "[Tt][Gg][Aa]",
    "[Ii][Ff][Ff]",
    "[Pp][Dd][Ff]",
]

# http://stackoverflow.com/a/3541239/262455
cache = {}
def os_walk_cache( dir ):
   if dir in cache:
      for x in cache[ dir ]:
         yield x
   else:
      cache[ dir ]    = []
      for x in os.walk( dir ):
         cache[ dir ].append( x )
         yield x
   raise StopIteration()

def fileexists(filepath):
    return os.path.isfile(filepath)

# http://stackoverflow.com/a/764374/262455
def multisub(my_string, mapping):
    for k, v in mapping:
        my_string = my_string.replace(k, v)
    return my_string

# http://stackoverflow.com/a/8653558/262455
def search(list, key, value):
    for item in list:
        if item[key] == value:
            return item

# http://stackoverflow.com/questions/2186525/use-a-glob-to-find-files-recursively-in-python
def findfile(volIndex, pattern):
    matches = []
    for root, dirnames, filenames in volIndex:
      for filename in fnmatch.filter(filenames, pattern):
          match = os.path.join(root, filename)
          matches.append(match)
    return matches

def print_error(message):
    print >> sys.stderr, message

def transcodeVersion(sg, version, formats):
    """
    Run the transcoding functions on each associated PublishedFile.
    """

    if not version.get('sg_path_to_frames') and not version.get('sg_path_to_movie') and not version.get('published_files'):
        print_error("Version ID %s has no Path to Frames, Path to Movie, or Published Files" % version.get('code'))
        return

    # find associated published files
    published_files = findPublishedFiles(sg, version.get('published_files'))
    mov_path_published_file = frame_path_published_file = None
    if "thumbnails" in formats:
        # generate thumbnails for each published file
        for published_file in published_files:
            (thumbnail, filmstrip) = \
                createFormatThumbnails(published_file,
                                       version.get('frame_range'))
            if thumbnail:
                print("Uploading thumbnail to Published File %s" % published_file.get('id'))
                sg.upload_thumbnail('PublishedFile', published_file.get('id'),
                                    thumbnail)
                published_file['thumbnail'] = thumbnail
            # end if
            if filmstrip:
                published_file['filmstrip'] = filmstrip
            # end if

            # determine which thumbnails should be shared with the Version record
            if published_file.get('path').get('local_path') == version.get('sg_path_to_movie'):
                mov_path_published_file = published_file
            elif published_file.get('path').get('local_path') == version.get('sg_path_to_frames'):
                frame_path_published_file = published_file
            # end if
        else:
            path = version.get('sg_path_to_movie') or version.get('sg_path_to_frames')
            (thumbnail_path, filmstrip_path) = createThumbnails(path)
            if thumbnail_path:
                print("Uploading thumbnail Version %s" % version.get('id'))
                sg.upload_thumbnail('Version', version.get('id'),
                                    thumbnail_path)
        # end for
    # endif

    mp4 = webm = None
    if "movies" in formats:
        # generate the mp4 and webm from the path to frames and path to movie field
        if version.get('sg_path_to_movie'):
            path_to_movie = version.get('sg_path_to_movie')#.replace("Volumes", "mnt")
            (mp4, webm) = createSRMedia(path_to_movie)
        elif version.get('sg_path_to_frames'):
            path_to_frames = version.get('sg_path_to_frames')#.replace("Volumes", "mnt")
            (mp4, webm) = createSRMedia(path_to_frames)
        #endif
    #endif

    # update the version with the generated files
    if mov_path_published_file:
        updateVersion(sg, version.get('id'),
                      mov_path_published_file.get('thumbnail'),
                      mov_path_published_file.get('filmstrip'),
                      mp4, webm)
    elif frame_path_published_file:
        updateVersion(sg, version.get('id'),
                      frame_path_published_file.get('thumbnail'),
                      frame_path_published_file.get('filmstrip'),
                      mp4, webm)
    else:
        updateVersion(sg, version.get('id'), None, None, mp4, webm,
                      frame=version.get('sg_path_to_frames'))
    print("Finished transcoding %s" % version.get('code'))
    return
# end transcodeVersion

def findPublishedFiles(sg, published_files):
    if not published_files:
        return []
    # end if

    pubfile_ids = [x.get('id') for x in published_files]

    filters = [['id', 'in', pubfile_ids]]
    fields = ['path', 'published_file_type.PublishedFileType.code']
    return (sg.find('PublishedFile', filters, fields) or [])
# end findPublishedFiles

def createFormatThumbnails(published_file, frame_range):
    filmstrip = thumbnail = None
    try:
        local_path = \
            published_file.get('path').get('local_path')#.replace("Volumes", "mnt")
        if frame_range:
            (thumbnail, filmstrip) = \
                createThumbnails(local_path, frame_range.split("-")[0])
        else:
            (thumbnail, filmstrip) = \
                createThumbnails(local_path)
        # end if
    except:
        print_error("Cannot create thumbnails for %s" % local_path)
    # end try

    if thumbnail and not os.path.exists(thumbnail):
        thumbnail = None
    if filmstrip and not os.path.exists(filmstrip):
        filmstrip = None
    return (thumbnail, filmstrip)
# end createFormatThumbnails

def createThumbnails(file_path, first_frame=None):
    frame_count = 25
    frame_width = 240
    quality = 50

    if not os.path.exists(os.path.dirname(file_path)):
        print("%s doesn't exist, skipping thumbnail creation" % file_path)
        return (None, None)
    # end if

    thumbnail_dir = os.path.join(os.path.dirname(file_path), ".thumbs")
    #print(thumbnail_dir)
    if not os.path.exists(thumbnail_dir):
        os.makedirs(thumbnail_dir)
    # end if

    filmstrip_path = os.path.join(os.path.dirname(file_path), "filmstrip.jpg")
    thumbnail_path = os.path.join(os.path.dirname(file_path), "thumbnail.jpg")

    duration = findDuration(file_path, first_frame)
    print(duration)
    if not duration:
        print("%s duration could not be determined, skipping thumbnail creation" % file_path)
        return (None, None)
    # end if
    (hours, minutes, seconds) = duration.split(":")

    print("Creating thumbnail...")
    seconds = float(hours)*60*60 + float(minutes)*60 + float(seconds)
    frame_width = 240

    thumb_cmd = ["nice", FFMPEG_BINARY, "-y"]
    if first_frame and int(first_frame):
        thumb_cmd.extend(["-start_number", first_frame])
    # end if
    thumb_cmd.extend(["-i", "'%s'" % file_path, "-vf",
                      "scale=%s:-1" % frame_width, "-r",
                      str(float(frame_count/seconds)), "-f", "image2",
                      "'%s/%%02d.jpg'" % thumbnail_dir])
    executeCommand(thumb_cmd)

    middle_thumb = "%s/%02d.jpg" % (thumbnail_dir, math.floor(float(frame_count/2)))
    first_thumb = "%s/%02d.jpg" % (thumbnail_dir, int(1))
    if os.path.exists(middle_thumb):
        shutil.copyfile(middle_thumb, thumbnail_path)
    elif os.path.exists(first_thumb):
        shutil.copyfile(first_thumb, thumbnail_path)
    # end if

    print("Creating filmstrip thumbnail...")
    items = os.listdir(thumbnail_dir)
    filmstrip_cmd = ["nice", FFMPEG_BINARY, "-y", "-i",
                     "%s/%%02d.jpg" % thumbnail_dir,
                     "-vf", "'tile=layout=%sx1'" % len(items)]
    filmstrip_cmd.append("%s" % filmstrip_path)
    executeCommand(filmstrip_cmd)

    return (thumbnail_path, filmstrip_path)
# end createThumbnails

def createSRMedia(file_path):
    mp4_path = os.path.join(os.path.dirname(file_path), "revolver.mp4")
    webm_path = os.path.join(os.path.dirname(file_path), "revolver.webm")
    # strip out the escape slashes so Platypus won't choke
    os.environ['FFMPEG_DATADIR'] = \
        os.path.dirname(FFMPEG_BINARY).replace("\\", "")

    # create mp4 file
    print("Creating mp4...")
    mp4_cmd = ["nice", FFMPEG_BINARY, "-y", "-i", "'%s'" % file_path,
               "-strict", "experimental",
               "-acodec", "aac", "-ab", "160k", "-ac", "2", "-vcodec",
               "libx264", "-pix_fmt", "yuv420p", "-vf",
               "'scale=trunc((a*oh)/2)*2:720'", "-g", "30", "-b:v", "2000k",
               "-vprofile", "high", "-bf", "0", "-f", "mp4",
               "'%s'" % mp4_path]
    executeCommand(mp4_cmd)

    # create webm file
    print("Creating webm...")
    webm_cmd = ["nice", FFMPEG_BINARY, "-y", "-i", "'%s'" % file_path,
                "-acodec", "libvorbis",
                "-aq", "60", "-ac", "2", "-pix_fmt", "yuv420p", "-vcodec",
                "libvpx", "-vf", "'scale=trunc((a*oh)/2)*2:720'", "-g",
                "30", "-b:v", "2000k", "-quality",
                "realtime", "-cpu-used", "0", "-qmin", "10", "-qmax", "42",
                "-f", "webm", "'%s'" % webm_path]
    print("FFMPEG_DATADIR: %s" % os.environ.get('FFMPEG_DATADIR'))
    executeCommand(webm_cmd)

    if mp4_path and not os.path.exists(mp4_path):
        mp4_path = None
    if webm_path and not os.path.exists(webm_path):
        webm_path = None
    return (mp4_path, webm_path)
# end createSRMedia

def updateVersion(sg, version_id, thumbnail, filmstrip, mp4, webm,
                  frame=None):
    if filmstrip:
        print("Uploading filmstrip thumbnail to version %s" % version_id)
        sg.upload_filmstrip_thumbnail('Version', version_id,
                                      filmstrip)
        os.remove(filmstrip)
    # end if
    if thumbnail:
        print("Uploading thumbnail to version %s" % version_id)
        sg.upload_thumbnail('Version', version_id, thumbnail)
        os.remove(thumbnail)
    # end if
    if mp4:
        print("Uploading MP4 file to version %s" % version_id)
        sg.upload('Version', version_id, mp4,
                       field_name='sg_uploaded_movie_mp4')
        os.remove(mp4)
    # end if
    if webm:
        print("Uploading WEBM file to version %s" % version_id)
        sg.upload('Version', version_id, webm,
                  field_name='sg_uploaded_movie_webm')
        os.remove(webm)
    # end if


    if not thumbnail and not filmstrip and not mp4 and not webm and frame:
        #frame = frame.replace("Volumes", "mnt")
        if os.path.exists(frame):
            print("No thumbnails found, adding to 'Uploaded File' field")
            try:
                sg.upload('Version', version_id, frame,
                          field_name='sg_uploaded_movie')
            except:
                print("File could not be added to the Uploaded File field. An unknown error was encountered")
            # end try
        # end if
    # end if

    #update_data = {'sg_transcode': False}
    #sg.update('Version', version_id, update_data)
# end updateVersion

def executeCommand(command):
    print(" ".join(command))
    cmd = subprocess.Popen(" ".join(command), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, shell=True,
                           env=os.environ)
    line = cmd.stdout.readline()
    while line:
        print(line.strip())
        line = cmd.stdout.readline()
    # end while
# end executeCommand

def findDuration(file_path, first_frame):
    duration_cmd = ["nice", FFMPEG_BINARY]
    if first_frame and int(first_frame):
        duration_cmd.extend(["-start_number", first_frame])
    # end if
    duration_cmd.extend(["-i", "'%s'" % file_path, "2>&1"])

    in_1 = ["grep", "Duration"]
    in_2 = ["cut", "-d", " ", "-f", "4"]
    in_3 = ["sed", "s/,//"]
    print(" | ".join([" ".join(duration_cmd), " ".join(in_1),
                                 " ".join(in_2), " ".join(in_3)]))
    os.environ["PATH"] = "%s:/usr/local/bin" % os.environ.get("PATH")
    duration_exec = subprocess.Popen(" ".join(duration_cmd),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, shell=True,
                                     env=os.environ)
    in_1_exec = subprocess.Popen(in_1, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=duration_exec.stdout)
    in_2_exec = subprocess.Popen(in_2, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=in_1_exec.stdout)
    in_3_exec = subprocess.Popen(in_3, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=in_2_exec.stdout)
    duration = in_3_exec.stdout.readlines()[0]
    return duration
# end findDuration


def process_action(server, session_token, path_to_folder):
    """
    Action the file search and upload to Shotgun via a session token
    You could instead instantiate Shotgun with a username/password
    """
    print("Connecting to Shotgun")
    sg = Shotgun(server, session_token=session_token)

    try:
        sg.connect()
    except:
        raise ValueError("Invalid Username or Password")

    print("*** Scanning "+path_to_folder+" ***")
    images = []
    movies = []
    version_fields = [
        "id",
        "code",
        "sg_path_to_movie",
        "sg_path_to_frames",
        "published_files",
    ]

    for imageType in imageTypes:
        images.extend(findfile(os_walk_cache(path_to_folder), "*."+imageType))
    for movieType in movieTypes:
        movies.extend(findfile(os_walk_cache(path_to_folder), "*."+movieType))

    baseFolder, subFolders, baseFiles = os_walk_cache(path_to_folder).next()
    for subFolder in subFolders:
        print("*** Scanning "+subFolder+" ***")
        for imageType in imageTypes:
            images.extend(findfile(os_walk_cache(subFolder), "*."+imageType))
        for movieType in movieTypes:
            movies.extend(findfile(os_walk_cache(subFolder), "*."+movieType))

    for image in images:
        imageBasename = os.path.basename(image)
        imageBasenameWithoutExt = os.path.basename(os.path.splitext(image)[0])
        # check for pre-existing version in shotgun
        version_filters = [
        ['project', 'is', {'type':'Project','id':project_id}],
            {
                "filter_operator": "any",
                "filters": [
                    [ "code", "is", imageBasenameWithoutExt ],
                    [ "code", "is", imageBasename ]
                ]
            }
        ]

        version = sg.find_one("Version", version_filters, version_fields)
        if version:
            print_error("Skipping existing version "+version['code'])
        else:
            # TODO create PublishedFile

            print("Creating version "+imageBasenameWithoutExt)
            data = {
                'code':imageBasenameWithoutExt,
                'sg_path_to_frames':image,
                'project':{'type':'Project','id':project_id}
            }
            version = sg.create("Version", data)
            print("Uploading thumbnail to version %s" % version['id'])
            sg.upload_thumbnail('Version', version['id'], image)

    for movie in movies:
        movieBasename = os.path.basename(movie)
        movieBasenameWithoutExt = os.path.basename(os.path.splitext(movie)[0])
        # check for pre-existing version in shotgun
        version_filters = [
        ['project', 'is', {'type':'Project','id':project_id}],
            {
                "filter_operator": "any",
                "filters": [
                    [ "code", "is", movieBasenameWithoutExt ],
                    [ "code", "is", movieBasename ]
                ]
            }
        ]

        version = sg.find_one("Version", version_filters, version_fields)
        if version:
            print_error("Skipping existing version "+version['code'])
        else:
            # TODO create PublishedFile

            print("Creating version "+movieBasenameWithoutExt)
            data = {
                'code':movieBasenameWithoutExt,
                'sg_path_to_frames':movie,
                'project':{'type':'Project','id':project_id}
            }
            version = sg.create("Version", data)

            # transcode version
            formats = ["thumbnails", "movies"]
            transcodeVersion(sg, version, formats)