from PIL import Image, ImageDraw, ImageFont


font=ImageFont.truetype("TianXiwei/fonts/IronFont.otf",110)
def add_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2, rad * 2), fill=255)
    alpha = Image.new('L', im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im
    
def Gabung(fun):
    def gabung(arg):
        im, text1 = add_corners(arg[0], 17), arg[1]


        font_path = "./TianXiwei/fonts/default.ttf"
        font_size = 120
        font = ImageFont.truetype(font_path, font_size)


        text_bbox = font.getbbox(text1)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]


        op = Image.new("RGB", (40, 20), color=(0, 0, 0))


        baru = Image.new(
            "RGB",
            (im.width + text_width + 210 + 20 + 130, 600),
            color=(0, 0, 0)
        )


        draw = ImageDraw.Draw(baru)
        draw.text((150, 250), text1, (255, 255, 255), font=font)


        baru.paste(im, (150 + text_width + 20, 230 + 10), im.convert("RGBA"))
        return baru

    return gabung(fun)

    
def generate(text1, text2):

    font_path = "./TianXiwei/fonts/default.ttf"
    font_size = 120
    font = ImageFont.truetype(font_path, font_size)


    text_bbox = font.getbbox(text2)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]


    oren = Image.new("RGBA", (text_width + 20, 140), color=(240, 152, 0))
    draw = ImageDraw.Draw(oren)


    text_x = 10
    text_y = (oren.height - text_height) // 2 - 10
    draw.text((text_x, text_y), text2, (0, 0, 0), font=font)


    return Gabung([oren, text1])


def blackpink(teks):

    font_path = "./TianXiwei/fonts/blackpink.otf"
    font_size = 120
    font = ImageFont.truetype(font_path, font_size)


    text_bbox = font.getbbox(teks)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]


    img = Image.new("RGB", (text_width + 100, text_height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)


    x = (img.width - text_width) // 2
    y = -25
    draw.text((x, y), teks, fill=(255, 148, 224), font=font)


    padded_width = img.width + 400
    padded_height = img.height + 400
    img2 = Image.new("RGB", (padded_width, padded_height), color=(0, 0, 0))


    paste_x = (img2.width - img.width) // 2
    paste_y = (img2.height - img.height) // 2
    img2.paste(img, (paste_x, paste_y))

    return img2
