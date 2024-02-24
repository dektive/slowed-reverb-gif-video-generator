from downloader import download_mp3
from colorthief import ColorThief
from PIL import Image
from temp import create_file
import os
import sfx
import ffmpeg


def apply_audio_effects(audio_fn, **kwargs) -> str:
    reserved_output_file = 'reserved.mp3'
    for kwarg in kwargs:
        getattr(sfx, kwarg)(audio_fn, reserved_output_file, kwargs[kwarg])
    return reserved_output_file


class VideoGenerator:
    def __init__(self, **kwargs):
        # input, output files
        self.gif = kwargs['gif']
        self._gif: ffmpeg.nodes.FilterableStream = ffmpeg.input(self.gif)
        self.length_required = int(kwargs['length'])

        self.pad_x = int(kwargs['pad_x'])
        self.pad_y = int(kwargs['pad_y'])

        self.baseline_ratio = (1920 - 2 * self.pad_x) / (1080 - 2 * self.pad_y)
        self.reserved_image_name = kwargs['reserved_image_name'] if 'reserved_image_name' in kwargs else 'reserved.png'
        self.reserved_video_name = kwargs['reserved_video_name'] if 'reserved_video_name' in kwargs else 'reserved.mp4'

        if 'background' in kwargs:
            if kwargs['background'] == 'default':
                self.background = Image.new('RGB', (1920, 1080), color=ColorThief(self.gif).get_color(quality=1) + (0,))
            else:
                self.background = Image.new('RGB', (1920, 1080), color=tuple(kwargs['background']))
            self.background.save(self.reserved_image_name)

        self.ffprobe = ffmpeg.probe(self.gif)
        self.duration = float(self.ffprobe['format']['duration'])
        self.number_of_frames = int(self.ffprobe['streams'][0]['nb_frames'])
        self.frame_rate = float(self.number_of_frames)/self.duration

        self.width = int(self.ffprobe['streams'][0]['coded_width'])
        self.height = int(self.ffprobe['streams'][0]['coded_height'])
        self.ratio = self.width / self.height

        self.temp_dir = 'temp'

    def _get_new_dimensions(self):
        """maintains aspect ratio while scaling width or height to maximum"""
        if self.ratio < self.baseline_ratio:
            # change dimensions based off of height; taller than it is fat
            new_height = 1080 - 2 * self.pad_y
            new_width = self.ratio * new_height
        else:
            # change dimensions based off of width; fatter than it is tall
            new_width = 1920 - 2 * self.pad_x
            new_height = (self.ratio ** float(-1)) * new_width

        return new_width, new_height

    def _generate_png_from_gif_palette(self):
        temp_file = create_file(self.temp_dir, '.png')
        Image.new('RGB', (1920, 1080), color=ColorThief(self.gif).get_color(quality=10)).save(temp_file)
        return temp_file


    def _resize_gif(self, x, y) -> ffmpeg.nodes.FilterableStream:
        """Resizes the GIF file, without cropping.
        Intended to be used WITH a background.
        For usage without background, use crop_gif"""
        resize_input_filter = ('scale', x, y)
        gif_resized = ffmpeg.input(self.gif).filter(*resize_input_filter)

        return gif_resized

    def _overlay_resized_gif_with_png(self):
        png = self._generate_png_from_gif_palette()
        w, h = self._get_new_dimensions()
        resized = self._resize_gif(w, h)

        png_background = ffmpeg.input(png,
                                      framerate=self.frame_rate,
                                      ss='00:00:00',
                                      to=self.duration,
                                      stream_loop=self.duration.__ceil__())

        return ffmpeg.filter(
            [png_background, resized],
            'overlay',
            (1920 - w) / 2,
            (1080 - h) / 2
        )

    def _loop(self, video: ffmpeg.nodes.FilterableStream):
        temp_file = create_file(self.temp_dir, '.mp4')
        video.output(temp_file).run(overwrite_output=True)
        video = ffmpeg.input(temp_file, stream_loop=-1, t=self.length_required)
        return video

    def generate_video_with_background(self, output_fn=False):
        video = self._loop(self._overlay_resized_gif_with_png())
        if output_fn:
            video.output(output_fn, c='copy').run(overwrite_output=True)
        else: return video

    def _generate_video_from_gif(self):
        temp_file = create_file(self.temp_dir, '.mp4')
        second_temp_file = create_file(self.temp_dir, '.mp4')

        video = ffmpeg.input(self.gif)
        video.output(temp_file).run(overwrite_output=True)
        # faster to make 2 sec gif -> mp4 THEN loop, instead of turning 2sec gif and looping during conversion
        ffmpeg.input(temp_file, stream_loop=-1, t=self.length_required).output(second_temp_file, c='copy').run(overwrite_output=True)
        return ffmpeg.input(second_temp_file)

    def generate_video_without_background(self, output_fn=False):
        video = self._generate_video_from_gif()
        if output_fn:
            video.output(output_fn, c='copy').run(overwrite_output=True)
        else:
            return video

    def __del__(self):
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))


def c2(audio_path: ffmpeg.nodes.FilterableStream, video_path: ffmpeg.nodes.FilterableStream, output_path):
    ffmpeg.output(video_path, audio_path, f'{output_path}', codec='copy').run(overwrite_output=True)


if __name__ == '__main__':
    from pydub import AudioSegment
    file = download_mp3("https://www.youtube.com/watch?v=XOzs1FehYOA")

    audio = apply_audio_effects(file, reverb=0.15, change_speed=0.85)
    length = len(AudioSegment.from_file(audio))

    g = VideoGenerator(
        background='default',
        gif='gifs/eren-eyes.gif',
        pad_y='75',
        pad_x='75',
        length=f'{(float(length) / float(1000)).__ceil__()}'
    )
    video = g.generate_video_with_background()
    c2(ffmpeg.input(audio), video, output_path='your song.mp4')