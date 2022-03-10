# coding=utf-8
import os
import sys
from shotgrid import sg
import fnmatch
import ffmpeg
import subprocess
import math
import tempfile
import shutil

ffmpeg_exe = r'"C:\Program Files\ffmpeg-4.4\bin\ffmpeg.exe"'

movieTypes = [
    "[Mm][Oo][Vv]",
    "[Mm][Pp][4]",
    "[Aa][Vv][Ii]"
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
geomTypes = [
    "[Mm][Bb]",
    "[Mm][Aa]",
    "[Aa][Bb][Cc]",
    "[Ff][Bb][Xx]"
]

def executeCommand(command):
    print(" ".join(command))
    cmd = subprocess.Popen(" ".join(command), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, shell=True,
                           env=os.environ)
    line = cmd.stdout.readline()
    while line:
        print(line.strip())
        line = cmd.stdout.readline()


def createSRMedia(file_path):
    folder_dest_mp4 = tempfile.mkdtemp()
    folder_dest_webm = tempfile.mkdtemp()
    mp4_path = os.path.join(folder_dest_mp4, os.path.basename(file_path).replace(os.path.splitext(file_path)[1], '.mp4'))
    webm_path = os.path.join(folder_dest_webm, os.path.basename(file_path).replace(os.path.splitext(file_path)[1], '.webm'))

    # create mp4 file
    print("Creating mp4...")
    mp4_cmd = [ ffmpeg_exe, "-y", "-i", "\"%s\"" % file_path,
               "-strict", "experimental",
               "-acodec", "aac", "-ab", "160k", "-ac", "2", "-vcodec",
               "libx264", "-pix_fmt", "yuv420p", "-vf",
               "\"scale=trunc((a*oh)/2)*2:720\"", "-g", "30", "-b:v", "2000k",
               "-vprofile", "high", "-bf", "0", "-f", "mp4",
               "\"%s\"" % mp4_path]
    executeCommand(mp4_cmd)

    # create webm file
    print("Creating webm...")
    webm_cmd = [ffmpeg_exe, "-y", "-i", "\"%s\"" % file_path,
                "-acodec", "libvorbis",
                "-aq", "60", "-ac", "2", "-pix_fmt", "yuv420p", "-vcodec",
                "libvpx", "-vf", "\"scale=trunc((a*oh)/2)*2:720\"", "-g",
                "30", "-b:v", "2000k", "-quality",
                "realtime", "-cpu-used", "0", "-qmin", "10", "-qmax", "42",
                "-f", "webm", "\"%s\"" % webm_path]
    executeCommand(webm_cmd)

    if mp4_path and not os.path.exists(mp4_path):
        mp4_path = None
    if webm_path and not os.path.exists(webm_path):
        webm_path = None
    return (mp4_path, webm_path)
# end createSRMedia

def createThumbnails(file_path):

    if not os.path.exists(os.path.dirname(file_path)):
        print("%s doesn't exist, skipping thumbnail creation" % file_path)
        return None

    #thumbnail_dir = tempfile.TemporaryDirectory()
    thumbnail_dir = tempfile.mkdtemp()
    thumbnail_path = os.path.join(thumbnail_dir, "thumbnail.jpg")


    #print("Creating thumbnail...")
    thumb_cmd = [ffmpeg_exe, "-y"]
    thumb_cmd.extend(["-i", "\"%s\"" % file_path, "-vf",
                      "\"scale=240:-1\"", "-r",
                      "25", "-f", "image2", "-frames:v 1 ",
                      "\"{}\"".format(thumbnail_path)])
    executeCommand(thumb_cmd)
    #print(thumbnail_path, os.path.exists(thumbnail_path))

    return thumbnail_path
# end createThumbnails

def scan_for_files(dir, pattern, images):
    files = os.listdir(dir)
    for file in files:
        if os.path.isdir(os.path.join(dir, file)):
            images = scan_for_files(os.path.join(dir, file), pattern, images)
        else:
            if fnmatch.filter([file], pattern):
                if images is None: images=[]
                images.append(os.path.join(dir, file))
    return images


def version(project, asset, task, folder_to_scan, images_only = False, movies_only = True, geometry_only = False):
    # gather images, movies and geometry
    # get images anyway as we might need thumbnails..
    gp_images = []
    for itype in imageTypes:
        pattern = "*." + itype
        scan_for_files(folder_to_scan, pattern, gp_images)

    images = []
    if not movies_only and not geometry_only:
        images = gp_images

    movies = []
    if not images_only and not geometry_only:
        for mtype in movieTypes:
            pattern = "*." + mtype
            scan_for_files(folder_to_scan, pattern, movies)

    geometries = []
    if not images_only and not movies_only:
        for gtype in geomTypes:
            pattern = "*." + gtype
            scan_for_files(folder_to_scan, pattern, geometries)

    # Published common data

    data = {'project': project,
            'description': 'automatic publishing ',
            'sg_status_list': 'ip',
            'entity': {'type': 'Asset', 'id': asset['id']},
            'task': {'type': 'Task', 'id': task['id']}}
    list_of_published = []
    if images + movies + geometries:
        for element in images + movies + geometries:
            data['code'] = '{}.{}.{}'.format(asset['code'], task['content'], os.path.basename(element))
            published = sg.sg.create('PublishedFile', data, return_fields=sg.get_fields('PublishedFile'))
            list_of_published.append(published)
            sg.sg.upload(entity_type="PublishedFile", entity_id=published['id'], path=element, field_name='path',
                         display_name=None, tag_list=None)

    # create now a new version
    f_path = None if not images else images[0]
    g_path = None if not geometries else geometries[0]
    m_path = None if not movies else movies[0]
    i_thumbnail = None
    if not gp_images:
        if movies:
            i_thumbnail = createThumbnails(movies[0])
    else:
        i_thumbnail = gp_images[0]
    m_thumbnail = None if not movies else movies[0]
    mov_path = None if not movies else movies[0]

    data = {'project': project,
            'code': asset['code'],
            'description': 'automatic versioninig ',
            'sg_path_to_movie': m_path,
            'sg_path_to_geometry': g_path,
            'sg_path_to_frames': f_path,
            'sg_status_list': 'rev',
            'entity': {'type': 'Asset', 'id': asset['id']},
            'sg_task': {'type': 'Task', 'id': task['id']}}
    data['published_files'] = [{'type': 'PublishedFile', 'id': x['id']} for x in list_of_published]
    version = sg.sg.create('Version', data)

    for published in list_of_published:
        sg.sg.update('PublishedFile', published['id'], data={'version': {'type': 'Version', 'id': version['id']}})
    if i_thumbnail:
        sg.sg.upload_thumbnail("Version", version['id'], i_thumbnail)
    if mov_path:
        # transcode mov_path into qtime
        mp4_path, webm_path = createSRMedia(mov_path)
        if mp4_path:
            sg.sg.upload(entity_type="Version", entity_id=version['id'], path=mp4_path, field_name='sg_uploaded_movie',
                         display_name=None, tag_list=None)
            if i_thumbnail:
                sg.sg.upload_filmstrip_thumbnail("Version", version['id'], i_thumbnail)
            try:
                os.remove(mp4_path)
            except:
                print('cannot delete temporary mp4 file {}'.format(mp4_path))
        if webm_path:
            sg.sg.upload(entity_type="Version", entity_id=version['id'], path=webm_path,
                         field_name='sg_uploaded_movie_webm', display_name=None, tag_list=None)
    if i_thumbnail:
        try:
            os.remove(i_thumbnail)
        except:
            print('cannot delete temporary thumbnail file {}'.format(i_thumbnail))
    return
