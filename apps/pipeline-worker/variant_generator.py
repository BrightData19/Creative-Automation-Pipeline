# /apps/pipeline-worker/variant_generator.py

from PIL import Image

# Common aspect ratios and their target dimensions
ASPECT_RATIOS = {
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
}

def generate_variants(base_image: Image.Image) -> dict[str, Image.Image]:
    """
    Generates variants for all target aspect ratios from a base image.
    The base image is center-cropped to fit the target aspect ratio.
    """
    variants = {}
    for ratio_name, target_dims in ASPECT_RATIOS.items():
        variants[ratio_name] = center_crop_and_resize(base_image, target_dims)
    return variants

def center_crop_and_resize(image: Image.Image, target_dims: tuple[int, int]) -> Image.Image:
    """
    Crops the image to the target aspect ratio from the center, then resizes it.
    """
    target_width, target_height = target_dims
    target_aspect = target_width / target_height
    
    original_width, original_height = image.size
    original_aspect = original_width / original_height

    # Determine cropping box
    if original_aspect > target_aspect:
        # Original image is wider than target, so crop width
        new_width = int(target_aspect * original_height)
        left = (original_width - new_width) / 2
        top = 0
        right = left + new_width
        bottom = original_height
    else:
        # Original image is taller than target, so crop height
        new_height = int(original_width / target_aspect)
        left = 0
        top = (original_height - new_height) / 2
        right = original_width
        bottom = top + new_height

    # Crop and resize
    cropped_image = image.crop((left, top, right, bottom))
    resized_image = cropped_image.resize(target_dims, Image.Resampling.LANCZOS)
    
    return resized_image
