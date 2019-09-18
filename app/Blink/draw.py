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

def draw_circle(draw, (x, y), color='blue'):
    r = 5
    draw.ellipse(((x-r, y-r), (x+r, y+r)), fill=color)

def draw_triangle(draw, (x, y)):
    draw.polygon(((x-6, y+5), (x, y-10), (x+6, y+5)), fill='black')

def draw_rectangle(draw, (x, y)):
    r = 5
    draw.rectangle(((x-r, y-r), (x+r, y+r)), fill='red')

def draw_text(draw, (x, y), text):
    font = ImageFont.truetype(TEXT_FONT, size=16)
    y_offset = font.getsize(text)[1] / 2
    draw.text((x, y-y_offset), text, fill='black', font=font)

def draw_line(draw, (x0, y0), (x1, y1)):
    draw.line(((x0, y0), (x1, y1)), width=3, fill='black')

def draw_legends(draw, with_tag):
    x = 710
    x_offset = 20
    base_y = 10
    margin = 25

    y = base_y
    draw_triangle(draw, (x, y))
    draw_text(draw, (x+x_offset, y), 'manager')

    y += margin
    draw_circle(draw, (x, y))
    draw_text(draw, (x+x_offset, y), 'anchor')

    if with_tag:
        y += margin
        draw_circle(draw, (x, y), color='red')
        draw_text(draw, (x+x_offset, y), 'actual tag position')

        y += margin
        draw_rectangle(draw, (x, y))
        draw_text(draw, (x+x_offset, y), 'computed tag position')

def draw_floor_map(config,
                   output_file_path,
                   ground_truth=None,
                   tag_position=None):
    im = open_floor_plan_image()

    draw = ImageDraw.Draw(im)

    closest_anchor_position = None

    for anchor in config.anchors:
        if len(anchor) > 2:
            if anchor[1] == ground_truth:
                assert not closest_anchor_position
                closest_anchor_position = anchor[2]
                draw_circle(draw, anchor[2], color='red')
            else:
                assert closest_anchor_position != anchor[2]
                draw_circle(draw, anchor[2])

    draw_triangle(draw, config.manager[2])

    if tag_position:
        draw_rectangle(draw, tag_position)
        draw_line(draw, closest_anchor_position, tag_position)
        with_tag = True
    else:
        with_tag = False

    draw_legends(draw, with_tag)

    im.save(output_file_path)

def main():
    draw_floor_map(utils.load_config(), 'deployment.png')

if __name__ == '__main__':
    main()
