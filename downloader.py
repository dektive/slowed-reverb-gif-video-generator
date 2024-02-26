import os.path
from pytube import YouTube
import ffmpeg


def download_mp3(youtube_link):
	t = YouTube(youtube_link)
	z = t.title
	t = t.streams.filter(only_audio=True)
	t[0].download(rf'./')
	(
		ffmpeg.input(f'{z}.mp4')
		.output(rf'./{z}.mp3')
		.run(overwrite_output=True)
	)
	return os.path.abspath(rf'./{z}.mp3')
