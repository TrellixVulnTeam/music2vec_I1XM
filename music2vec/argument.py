import torch as th
import numpy as np
import librosa
from torchvision.transforms import ToTensor, ToPILImage, Resize, Normalize
from scipy import interpolate


class TimeStreach(object):

    def __init__(
        self,
        rate_width=0.2 # 0.5 ~ 1.5
    ):

        self.rate_width = rate_width
        self.rate = np.random.uniform(1-self.rate_width/2, 1+self.rate_width/2)

    def __call__(self, data):

        sample_length = data.shape[-1]

        processed_data = librosa.effects.time_stretch(data, self.rate)
        if self.rate > 1:
            processed_data = np.pad(
                processed_data, 
                (0, sample_length - processed_data.shape[-1]), 
                'wrap'
            )
        else:
            processed_data = processed_data[:sample_length]
        
        return processed_data


class PitchShift(object):

    def __init__(
        self,
        step_width=6 # -3 ~ 3
    ):

        self.step_width = step_width
        self.step = int(np.random.uniform(-self.step_width/2, self.step_width/2))


    def __call__(self, data):

        processed_data = librosa.effects.pitch_shift(data, sr=22050, n_steps=self.step)
        
        return processed_data


class Mask(object):

    def __init__(
        self,
        mask_rate=0.3
    ):

        self.mask_rate = mask_rate


    def __call__(self, data):
        
        sample_length = data.shape[-1]
        mask_length = int(sample_length*self.mask_rate)
        mask_start = np.random.randint(
            0, sample_length-mask_length
        )
        
        data[mask_start:mask_start+mask_length] = np.zeros(mask_length)

        return data


class Crop(object):
    """Crop
    Crop samples
    Args:
        length (int): length for crop sample.
        start (int, optional): index for start crop.
                              Default: `0`
    Returns:
        numpy.ndarray with shape (length).
    """
    def __init__(self,
                length: int,
                *,
                start: int=0):
        self.length: int = length
        self.start: int = start

    def __call__(self, data):
        if self.start > len(data):
            raise IndexError('`start` out of range.')
        if self.start < 0 or self.length < 0:
            raise ValueError('`start` and `length` must be positive int.')
        return data[self.start:self.start+self.length]


class RandomCrop(object):
    """RandomCrop
    Crop samples randamly
    Args:
        length (int): length for crop sample.
    Returns:
        numpy.ndarray with shape (length).
    """
    def __init__(self,
                length=None):
        self.length: int = length if length is not None else 0

    def __call__(self, data):
        start = np.random.randint(0, np.abs(len(data)-self.length))
        if self.length < 0:
            raise ValueError('`length` must be positive int.')
        if len(data)-self.length < 0:
            raise ValueError('`length` too large.')
        return Crop(length=self.length, start=start)(data)


class ToConstantQ(object):

    def __init__(
        self,
        size=(128, 128)
    ):

        self.size = size
        self.channel = 1024 // self.size[0]
        

    def __call__(self, audio):

        image = th.zeros(4, self.size[0], self.size[1])

        # x = librosa.stft(audio)
        x = librosa.feature.melspectrogram(audio, n_mels=512, hop_length=1024)
        amp = np.abs(x)
        amp = self.norm(amp)[:512, :]

        for i in range(4):
            a = amp[i*128:(i+1)*128, :]
            a = ToPILImage()(a)
            a = Resize(self.size)(a)
            a = ToTensor()(a)
            a = Normalize((0.5), (0.5))(a)
            image[i] += a[0] 

        return image


    def norm(self, x):
        x = librosa.power_to_db(x, ref=np.max)
        current_freq = np.linspace(20, 22050//2, 512)
        log_scale = np.logspace(1.7, 4.04, 512)
        for i in range(130):
            f = interpolate.interp1d(current_freq, x[:,i])
            x[:,i] = f(log_scale)
        x = ( x - np.min(x) ) / ( np.max(x) - np.min(x) )
        x = np.uint8(x*255)
        return x 