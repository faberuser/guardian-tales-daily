# Function taken from PyAutoGUI library (https://pyautogui.readthedocs.io/en/latest/#)

from sys import version_info
from time import time
from PIL import Image
from cv2 import (imread, cvtColor, matchTemplate,
    IMREAD_COLOR, IMREAD_GRAYSCALE, COLOR_BGR2GRAY, TM_CCOEFF_NORMED)
from numpy import ndarray, array, arange, unravel_index

LOAD_COLOR = IMREAD_COLOR
LOAD_GRAYSCALE = IMREAD_GRAYSCALE
USE_IMAGE_NOT_FOUND_EXCEPTION = False
GRAYSCALE_DEFAULT = False

class ImageNotFoundException(Exception):
    pass # This is an exception class raised when the locate functions fail to locate an image.

def locateOnScreen(image, full_image, minSearchTime=0, **kwargs):
    start = time()
    while True:
        try:
            _full_image = Image.open(full_image)
            retVal = locate(image, _full_image, **kwargs)
            try:
                _full_image.fp.close()
            except AttributeError:
                pass
            if retVal or time() - start > minSearchTime:
                return retVal
        except ImageNotFoundException:
            if time() - start > minSearchTime:
                if USE_IMAGE_NOT_FOUND_EXCEPTION:
                    raise
                else:
                    return None

def locate(needleImage, haystackImage, **kwargs):
    """
    TODO
    """
    # Note: The gymnastics in this function is because we want to make sure to exhaust the iterator so that the needle and haystack files are closed in locateAll.
    kwargs['limit'] = 1
    points = tuple(_locateAll_opencv(needleImage, haystackImage, **kwargs))
    if len(points) > 0:
        return points[0]
    else:
        if USE_IMAGE_NOT_FOUND_EXCEPTION:
            raise ImageNotFoundException('Could not locate the image.')
        else:
            return None

def _load_cv2(img, grayscale=None):
    """
    TODO
    """
    # load images if given filename, or convert as needed to opencv
    # Alpha layer just causes failures at this point, so flatten to RGB.
    # RGBA: load with -1 * cv2.CV_LOAD_IMAGE_COLOR to preserve alpha
    # to matchTemplate, need template and image to be the same wrt having alpha

    if grayscale is None:
        grayscale = GRAYSCALE_DEFAULT
    if isinstance(img, (str, str)):
        # The function imread loads an image from the specified file and
        # returns it. If the image cannot be read (because of missing
        # file, improper permissions, unsupported or invalid format),
        # the function returns an empty matrix
        # http://docs.opencv.org/3.0-beta/modules/imgcodecs/doc/reading_and_writing_images.html
        if grayscale:
            img_cv = imread(img, LOAD_GRAYSCALE)
        else:
            img_cv = imread(img, LOAD_COLOR)
        if img_cv is None:
            raise IOError("Failed to read %s because file is missing, "
                          "has improper permissions, or is an "
                          "unsupported or invalid format" % img)
    elif isinstance(img, ndarray):
        # don't try to convert an already-gray image to gray
        if grayscale and len(img.shape) == 3:  # and img.shape[2] == 3:
            img_cv = cvtColor(img, COLOR_BGR2GRAY)
        else:
            img_cv = img
    elif hasattr(img, 'convert'):
        # assume its a PIL.Image, convert to cv format
        img_array = array(img.convert('RGB'))
        img_cv = img_array[:, :, ::-1].copy()  # -1 does RGB -> BGR
        if grayscale:
            img_cv = cvtColor(img_cv, COLOR_BGR2GRAY)
    else:
        raise TypeError('expected an image filename, OpenCV numpy array, or PIL image')
    return img_cv

def _locateAll_opencv(needleImage, haystackImage, grayscale=None, limit=10000, region=None, step=1,
                      confidence=0.999):
    """
    TODO - rewrite this
        faster but more memory-intensive than pure python
        step 2 skips every other row and column = ~3x faster but prone to miss;
            to compensate, the algorithm automatically reduces the confidence
            threshold by 5% (which helps but will not avoid all misses).
        limitations:
          - OpenCV 3.x & python 3.x not tested
          - RGBA images are treated as RBG (ignores alpha channel)
    """
    if grayscale is None:
        grayscale = GRAYSCALE_DEFAULT

    confidence = float(confidence)

    needleImage = _load_cv2(needleImage, grayscale)
    needleHeight, needleWidth = needleImage.shape[:2]
    haystackImage = _load_cv2(haystackImage, grayscale)

    if region:
        haystackImage = haystackImage[region[1]:region[1]+region[3],
                                      region[0]:region[0]+region[2]]
    else:
        region = (0, 0)  # full image; these values used in the yield statement
    if (haystackImage.shape[0] < needleImage.shape[0] or
        haystackImage.shape[1] < needleImage.shape[1]):
        # avoid semi-cryptic OpenCV error below if bad size
        raise ValueError('needle dimension(s) exceed the haystack image or region dimensions')

    if step == 2:
        confidence *= 0.95
        needleImage = needleImage[::step, ::step]
        haystackImage = haystackImage[::step, ::step]
    else:
        step = 1

    # get all matches at once, credit: https://stackoverflow.com/questions/7670112/finding-a-subimage-inside-a-numpy-image/9253805#9253805
    result = matchTemplate(haystackImage, needleImage, TM_CCOEFF_NORMED)
    match_indices = arange(result.size)[(result > confidence).flatten()]
    matches = unravel_index(match_indices[:limit], result.shape)

    if len(matches[0]) == 0:
        if USE_IMAGE_NOT_FOUND_EXCEPTION:
            raise ImageNotFoundException('Could not locate the image (highest confidence = %.3f)' % result.max())
        else:
            return

    # use a generator for API consistency:
    matchx = matches[1] * step + region[0]  # vectorized
    matchy = matches[0] * step + region[1]
    for x, y in zip(matchx, matchy):
        yield (x, y, needleWidth, needleHeight)