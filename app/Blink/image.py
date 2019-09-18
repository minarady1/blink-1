#!/usr/bin/env python
# coding: utf-8

from PIL import Image, ImageDraw, ImageFont

import utils

FLOOR_PLAN = 'images/floor_plan.png'
TEXT_FONT = 'DejaVuSansMono'

def open_floor_plan_image():
    im = Image.open(FLOOR_PLAN)
    # convert the image to the 'RGB' mode so as to use color names such as
    #'red'
    im = im.quantize()
    return im.convert('RGB')

def draw_circle(draw, (x, y)):
    r = 5
    draw.ellipse(((x-r, y-r), (x+r, y+r)), fill='red')

def draw_triangle(draw, (x, y)):
    draw.polygon(((x-6, y+5), (x, y-10), (x+6, y+5)), fill='blue')

def draw_text(draw, (x, y), text):
    font = ImageFont.truetype(TEXT_FONT, size=16)
    y_offset = font.getsize(text)[1] / 2
    draw.text((x, y-y_offset), text, fill='black', font=font)

def draw_legends(draw):
    x = 750
    x_offset = 20
    base_y = 30
    margin = 25

    y = base_y
    draw_circle(draw, (x, y))
    draw_text(draw, (x+x_offset, y), 'anchor')

    y = base_y + margin
    draw_triangle(draw, (x, y))
    draw_text(draw, (x+x_offset, y), 'manager')

def draw_deployment_png():
    output_file_name = 'deployment.png'
    config = utils.load_config()
    im = open_floor_plan_image()

    draw = ImageDraw.Draw(im)
    for anchor in config.anchors:
        if len(anchor) > 2:
            draw_circle(draw, anchor[2])
    draw_triangle(draw, config.manager[2])
    draw_legends(draw)

    print 'draw {}'.format(output_file_name)
    im.save(output_file_name)

if __name__ == '__main__':
    draw_deployment_png()
