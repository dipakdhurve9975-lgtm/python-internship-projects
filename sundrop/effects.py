"""Small Pillow display effects. Input frames and saved media stay untouched."""
from PIL import Image, ImageDraw, ImageFont, ImageOps

def cd_landscape(frame,size=(640,360)):
    """Rotate the supplied portrait visual clockwise and fill the display only."""
    rotated=frame.convert('RGB').transpose(Image.Transpose.ROTATE_270)
    return ImageOps.fit(rotated,size,method=Image.Resampling.LANCZOS)

def video_effect(frame,mode='Normal',size=(640,360)):
    source=ImageOps.contain(frame.convert('RGB'),size)
    if mode=='Pixel':
        tiny=source.resize((max(1,source.width//10),max(1,source.height//10)),Image.Resampling.BOX)
        return tiny.resize(source.size,Image.Resampling.NEAREST)
    if mode!='ASCII':return source
    font=ImageFont.load_default(size=10);cell_w,cell_h=6,11
    grid=source.resize((max(1,source.width//cell_w),max(1,source.height//cell_h)),Image.Resampling.BOX)
    gray=grid.convert('L');out=Image.new('RGB',source.size,'#172522');draw=ImageDraw.Draw(out)
    ramp=' .:-=+*#%@'
    for y in range(grid.height):
        for x in range(grid.width):
            draw.text((x*cell_w,y*cell_h),ramp[gray.getpixel((x,y))*9//255],font=font,fill=grid.getpixel((x,y)))
    return out

