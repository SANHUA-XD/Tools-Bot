import io
from pyrogram.types import Message
from PIL import Image, ImageEnhance, ImageFilter

async def getFile(message: Message):

    if not message.reply_to_message:
        return None


    if message.reply_to_message.photo:
        image = await message.reply_to_message.download()
        return image
    elif message.reply_to_message.document and message.reply_to_message.document.mime_type in ['image/png', 'image/jpg', 'image/jpeg']:
        image = await message.reply_to_message.download()
        return image
    else:
        return None

async def UpscaleImages(image) -> str:

    try:

        if isinstance(image, bytes):
            img = Image.open(io.BytesIO(image))
        else:
            img = Image.open(image)
        

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        width, height = img.size
        

        img_resized = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        

        img_smoothed = img_resized.filter(ImageFilter.SMOOTH_MORE)
        

        img_deblurred = img_smoothed.filter(ImageFilter.UnsharpMask(radius=2.5, percent=170, threshold=3))
        

        color_enhancer = ImageEnhance.Color(img_deblurred)
        img_colored = color_enhancer.enhance(1.15)
        

        contrast_enhancer = ImageEnhance.Contrast(img_colored)
        img_contrasted = contrast_enhancer.enhance(1.10)
        

        sharpness_enhancer = ImageEnhance.Sharpness(img_contrasted)
        img_final = sharpness_enhancer.enhance(1.8)
        

        upscaled_file_path = "upscaled.png"
        img_final.save(upscaled_file_path, "PNG", quality=100)
        
        return upscaled_file_path
    except Exception as e:
        raise Exception(f"Failed to upscale the image: {e}")

