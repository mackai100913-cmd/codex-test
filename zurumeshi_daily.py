#!/usr/bin/env python3
from __future__ import annotations

import argparse, io, json, os, textwrap
from datetime import date, datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from google import genai
from google.genai import types

W, H = 864, 1536
OUT = Path('output')

# 日付が唯一のレシピ選定ルール。番号順・過去出力からは選ばない。
SCHEDULE = {
'2026-08-22': ('017','せせりアスパラレモンバター','週末贅沢'),
'2026-08-23': ('018','パリパリライスペーパー餃子','週末贅沢'),
'2026-08-24': ('019','トンデリング（玉ねぎ豚バラ肉巻き）','SNSバズ飯'),
'2026-08-25': ('020','5分で濃厚かんたん担々麺','麺ズル'),
'2026-08-26': ('021','松屋「うまトマハンバーグ」風','お店再現'),
'2026-08-27': ('022','ささみ海苔カツ','節約変換'),
'2026-08-28': ('023','大戸屋「鶏と野菜の黒酢あん」風','お店再現'),
'2026-08-29': ('024','ネギクリームチーズベーコン','SNSバズ飯'),
'2026-08-30': ('025','サイゼリヤ「ミラノ風ドリア」風','お店再現'),
'2026-08-31': ('026','具だくさんばくだんおにぎり','平日ラク旨'),
'2026-09-01': ('027','焦がし海苔バターうどん','麺ズル'),
'2026-09-02': ('028','餃子の王将「天津飯」風','お店再現'),
'2026-09-03': ('029','モッツァレラうま塩鶏','節約変換'),
'2026-09-04': ('030','KFC「カーネルクリスピー」風ザクザクチキン','お店再現'),
'2026-09-05': ('031','まるごとトマトチーズ焼きおにぎり','SNSバズ飯'),
'2026-09-06': ('032','吉野家「牛カルビ丼」風','お店再現'),
'2026-09-07': ('033','豚こま焦がし玉ねぎステーキ丼','平日ラク旨'),
'2026-09-08': ('034','丸亀製麺「明太釜玉うどん」風','お店再現'),
'2026-09-09': ('035','卵と豆腐のふわとろ天津飯','平日ラク旨'),
'2026-09-10': ('036','厚揚げ肉巻きヤンニョム','節約変換'),
'2026-09-11': ('037','すき家「ねぎ玉牛丼」風','お店再現'),
'2026-09-12': ('038','冷凍餃子のチーズ羽根ラザニア','SNSバズ飯'),
'2026-09-13': ('039','モスバーガー「モスバーガー」風','お店再現'),
'2026-09-14': ('040','とろたま甘酢そぼろ丼','平日ラク旨'),
'2026-09-15': ('041','ツナレモン塩昆布パスタ','麺ズル'),
'2026-09-16': ('042','CoCo壱番屋「チーズカレー」風','お店再現'),
'2026-09-17': ('043','えのきのカリカリガレット','節約変換'),
'2026-09-18': ('044','鳥貴族「山芋の鉄板焼」風','お店再現'),
'2026-09-19': ('045','とろ〜りチーズボール','SNSバズ飯'),
'2026-09-20': ('046','一蘭風 濃厚豚骨ラーメン','お店再現'),
'2026-09-21': ('047','卵2個のとろとろ他人丼','平日ラク旨'),
'2026-09-22': ('048','ワンパン海苔ボナーラ','麺ズル'),
'2026-09-23': ('049','ローソン「からあげクン」風','お店再現'),
'2026-09-24': ('050','厚揚げチーズ唐揚げ','節約変換'),
'2026-09-25': ('051','コメダ珈琲店「たっぷりたまごのピザトースト」風','お店再現'),
'2026-09-26': ('052','カリカリ餃子の皮タコス','SNSバズ飯'),
'2026-09-27': ('053','びっくりドンキー「おろしそバーグディッシュ」風','お店再現'),
'2026-09-28': ('054','もやし豚巻き黒酢照り焼き','平日ラク旨'),
'2026-09-29': ('055','焦がし白だしカチョエペペ','麺ズル'),
'2026-09-30': ('056','セブン「金のハンバーグ」風 濃厚デミハンバーグ','お店再現'),
'2026-10-01': ('057','ちくわ明太チーズ磯辺焼き','節約変換'),
'2026-10-02': ('058','ファミマ「スパイシーチキン」風','お店再現'),
'2026-10-03': ('059','食パンのカリパリ羽根ピザ','SNSバズ飯'),
'2026-10-04': ('060','丸源ラーメン「肉そば」風','お店再現'),
'2026-10-05': ('061','豚こまチーズタッカルビ風','平日ラク旨'),
'2026-10-06': ('062','牛乳と味噌の3分リゾット','平日ラク旨'),
'2026-10-07': ('063','松屋「シュクメルリ」風','お店再現'),
'2026-10-08': ('064','大根の焦がしバターステーキ','節約変換'),
'2026-10-09': ('065','サイゼリヤ「辛味チキン」風','お店再現'),
'2026-10-10': ('066','カマンベール丸ごとキムチ鍋','SNSバズ飯'),
'2026-10-11': ('067','551蓬莱「豚まん」風','お店再現'),
'2026-10-12': ('068','玉ねぎ1個のオニオングラタン丼','平日ラク旨'),
}

DOW = ['月','火','水','木','金','土','日']

FONT_SERIF = [
'/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc',
'/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc',
'/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf']
FONT_SANS = [
'/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
'/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf']

def font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def serif(size): return font(FONT_SERIF, size)
def sans(size): return font(FONT_SANS, size)

def fit(img, size): return ImageOps.fit(img.convert('RGB'), size, method=Image.Resampling.LANCZOS)

def wrap(draw, text, fnt, maxw):
    out=[]; cur=''
    for ch in text:
        if ch=='\n': out.append(cur); cur=''; continue
        t=cur+ch
        if draw.textlength(t,font=fnt)<=maxw: cur=t
        else:
            if cur: out.append(cur)
            cur=ch
    if cur: out.append(cur)
    return out

def draw_gold_text(base, xy, text, fnt, stroke=2):
    x,y=xy
    mask=Image.new('L', base.size, 0); md=ImageDraw.Draw(mask)
    md.text((x,y),text,font=fnt,fill=255,stroke_width=stroke,stroke_fill=255)
    bbox=mask.getbbox()
    if not bbox: return
    grad=Image.new('RGB',base.size,(0,0,0)); gd=ImageDraw.Draw(grad)
    y0,y1=bbox[1],bbox[3]; h=max(1,y1-y0)
    stops=[(0.0,(255,233,154)),(.20,(246,198,75)),(.75,(233,168,0)),(1.0,(201,122,0))]
    for yy in range(y0,y1):
        t=(yy-y0)/h
        for i in range(len(stops)-1):
            a,ca=stops[i]; b,cb=stops[i+1]
            if a<=t<=b:
                q=(t-a)/(b-a); c=tuple(int(ca[k]*(1-q)+cb[k]*q) for k in range(3)); break
        gd.line((0,yy,W,yy),fill=c)
    base.paste(grad,(0,0),mask)

def gemini_client():
    key=os.environ.get('GEMINI_API_KEY')
    if not key: raise RuntimeError('GEMINI_API_KEY missing')
    return genai.Client(api_key=key)

def gen_image(client, prompt, aspect):
    cfg=types.GenerateContentConfig(response_modalities=['IMAGE'])
    try: cfg.image_config=types.ImageConfig(aspect_ratio=aspect)
    except Exception: pass
    model=os.environ.get('GEMINI_IMAGE_MODEL','gemini-3-pro-image-preview')
    resp=client.models.generate_content(model=model,contents=prompt,config=cfg)
    for part in resp.candidates[0].content.parts:
        inline=getattr(part,'inline_data',None)
        if inline and inline.data:
            return Image.open(io.BytesIO(inline.data)).convert('RGB')
    raise RuntimeError('Gemini returned no image')

def fixed_recipe_017():
    return {
      'title_gold':'せせりアスパラ','title_white':'レモンバター',
      'subcopy':'週末20分！香ばしいせせり×爽やかレモンバター',
      'right_copy':'週末は、レモンバターでちょい贅沢。',
      'description':'ぷりっと香ばしいせせりに、アスパラの食感とレモンバターのコク。家飲みにも白ごはんにも強い一皿。',
      'time':'約20分','cost':'約750円','difficulty':2,
      'benefits':['せせりの香ばしい焼き目が最高！','アスパラはシャキッと食感！','レモンバターで後味さっぱり！'],
      'ingredients':[
        ['鶏せせり','250g'],['アスパラ','5本'],['レモン','1/2個'],['にんにく','1片'],
        ['バター','15g'],['オリーブ油','小さじ1'],['塩','小さじ1/3'],['黒こしょう','少々'],['しょうゆ','小さじ1']
      ],
      'steps':[
        ['下ごしらえ','せせりは大きければ食べやすく切り、塩・黒こしょうを振る。アスパラは根元を落として4cm幅に切る。'],
        ['レモンを準備','レモンは薄い半月切りを2〜3枚取り、残りは果汁を搾る。にんにくは薄切りにする。'],
        ['せせりを焼く','フライパンにオリーブ油を熱し、せせりを広げて中火で焼く。焼き色が付くまで触りすぎない。'],
        ['アスパラを加える','せせりを返し、アスパラとにんにくを加えて炒め、せせりの中心までしっかり火を通す。'],
        ['レモンバター','弱火にしてバター、しょうゆ、レモン果汁を加え、全体に艶が出るまでさっと絡める。'],
        ['盛り付け','器に盛り、レモンを添えて黒こしょうを追加。熱いうちに仕上げる。']
      ],
      'points':['せせりは最初に動かしすぎず、焼き目をつける。','バターとレモンは最後に入れて香りを残す。','アスパラは炒めすぎず鮮やかな緑と食感を残す。'],
      'extra':'仕上げにレモン皮を少量すりおろすと、香りが一段上がる。',
      'pairings':['白ごはん','オニオンスープ','トマトサラダ','レモンサワー']
    }

def gen_recipe(client, dish, category):
    if dish=='せせりアスパラレモンバター': return fixed_recipe_017()
    prompt=f'''日本の料理SNS「ズルめし」用。料理名は必ず「{dish}」、カテゴリは「{category}」。2人分の現実的なレシピを作り、JSONだけ返す。店名がある場合は公式と誤認させず必ず「風」表現を維持。\nキー: title_gold, title_white, subcopy, right_copy, description, time, cost, difficulty(1-5), benefits(3個), ingredients([[名称,分量]] 8-12個), steps([[短い見出し,本文]] ちょうど6個), points(3個), extra, pairings(4個)。\n料理名全体が title_gold+title_white で自然に読めること。平日の時短表現は実時間と矛盾させない。肉魚卵は十分加熱。'''
    model=os.environ.get('GEMINI_TEXT_MODEL','gemini-3-pro')
    r=client.models.generate_content(model=model,contents=prompt)
    txt=(r.text or '').strip(); txt=txt[txt.find('{'):txt.rfind('}')+1]
    data=json.loads(txt)
    if len(data.get('steps',[]))!=6 or len(data.get('benefits',[]))!=3: raise RuntimeError('recipe schema invalid')
    return data

def photo_prompt(dish, recipe):
    return f'''Photorealistic Japanese food photography of {dish}. Dark nearly black background, warm backlight, shallow depth of field, real home-cooked texture, natural gloss only. No text, no logo, no watermark, no hands, no packages. Hero plate fills lower area; clearly show the signature appetite cue of this dish. Ingredients and appearance must match: {recipe['description']}. High realism, no CGI, no plastic food, no repeated artificial shapes. Vertical 9:16.'''

def steps_prompt(dish, recipe):
    desc=' / '.join([f"{i+1}:{s[0]}—{s[1]}" for i,s in enumerate(recipe['steps'])])
    return f'''Create ONE photorealistic 2-column by 3-row contact sheet containing exactly six cooking-process photos for Japanese dish {dish}, in order left-to-right top-to-bottom. NO text, NO numbers, NO logos, NO people/hands. Each panel must visually match its step and use the same dark kitchen lighting and ingredients; do not show another dish. Steps: {desc}. Clean equal panel grid, 3:4 overall aspect ratio.'''

def pairing_prompt(items):
    return f'''Create ONE photorealistic 2x2 food contact sheet, no text, showing exactly these four pairings in order: {', '.join(items)}. Dark restaurant-style background, clean individual dishes, no people, no logos, equal square panels, overall 1:1.'''

def split_grid(img, rows, cols):
    im=fit(img,(cols*400,rows*400)); out=[]
    for r in range(rows):
        for c in range(cols): out.append(im.crop((c*400,r*400,(c+1)*400,(r+1)*400)))
    return out

def brush_label(draw, text, x=28,y=58):
    box=(x,y,x+260,y+64)
    pts=[(x,y+7),(x+12,y),(x+245,y+3),(x+260,y+17),(x+249,y+51),(x+12,y+62),(x,y+52)]
    draw.polygon(pts,fill='#F5F1EA')
    draw.text((x+22,y+9),text,font=serif(35),fill='#111111')

def render_cover(day, recipe, hero):
    base=fit(hero,(W,H)).convert('RGB')
    # upper scrim, preserving the large food image below
    ov=Image.new('RGBA',(W,H),(0,0,0,0)); od=ImageDraw.Draw(ov)
    for y in range(0,900):
        a=int(238*(1-y/1000)); od.line((0,y,W,y),fill=(0,0,0,max(60,a)))
    base=Image.alpha_composite(base.convert('RGBA'),ov).convert('RGB')
    d=ImageDraw.Draw(base)
    dow=DOW[day.weekday()]
    brush_label(d,f'{dow}曜のごちそう')
    rc=recipe['right_copy']; rf=sans(28)
    for i,line in enumerate(wrap(d,rc,rf,320)[:2]): d.text((512,64+i*38),line,font=rf,fill='#F4D800')
    d.line((520,144,760,144),fill='#F4D800',width=3)
    sf=sans(25); d.text((44,185),recipe['subcopy'],font=sf,fill='#F5F2EB')
    draw_gold_text(base,(44,235),recipe['title_gold'],serif(76),stroke=2)
    d=ImageDraw.Draw(base); d.text((44,327),recipe['title_white'],font=serif(92),fill='#F7F2E8',stroke_width=2,stroke_fill='#111111')
    d.text((44,448),'やみつき確定',font=serif(43),fill='#E51B16'); d.text((300,450),'の一皿。',font=serif(32),fill='#F6F2EA')
    y=530
    bf=sans(27)
    for b in recipe['benefits'][:3]:
        d.rectangle((48,y+7,72,y+31),outline='#F1D400',width=2); d.line((53,y+20,61,y+28,70,y+10),fill='#F1D400',width=3)
        for j,line in enumerate(wrap(d,b,bf,680)[:2]): d.text((84,y+j*32),line,font=bf,fill='#F6F2EA')
        y+=70
    return base

def draw_panel(d,box): d.rounded_rectangle(box,radius=8,outline='#B88721',width=2,fill='#0E0F10')

def render_card(day, recipe, hero, steps, pairings):
    img=Image.new('RGB',(W,H),'#08090A'); d=ImageDraw.Draw(img)
    left=532; rightx=542
    # left heading
    d.text((26,32),recipe['subcopy'],font=sans(20),fill='#F4F0E8')
    draw_gold_text(img,(26,72),recipe['title_gold'],serif(47),stroke=1); d=ImageDraw.Draw(img)
    d.text((26,126),recipe['title_white'],font=serif(57),fill='#F7F2E8')
    d.text((26,194),'やみつき確定',font=serif(29),fill='#E51B16'); d.text((199,197),'の一皿。',font=serif(22),fill='#F5F1E9')
    # description
    yf=236
    for line in wrap(d,recipe['description'],sans(18),490)[:3]: d.text((26,yf),line,font=sans(18),fill='#DDD8CF'); yf+=27
    hero_box=fit(hero,(490,330)); img.paste(hero_box,(26,320))
    # metrics
    y=668; draw_panel(d,(26,y,516,y+102)); cw=490/3
    metrics=[('調理時間',recipe['time']),('費用目安(2人分)',recipe['cost']),('難易度','★'*int(recipe['difficulty'])+'☆'*(5-int(recipe['difficulty'])))]
    for i,(a,b) in enumerate(metrics):
        x=26+i*cw
        if i: d.line((x,y+12,x,y+90),fill='#B88721',width=1)
        d.text((x+12,y+14),a,font=sans(16),fill='#D8A83A'); d.text((x+12,y+49),b,font=sans(21),fill='#F4F0E8')
    # ingredients two columns
    y=790; d.text((26,y),'材料（2人分）',font=serif(25),fill='#D8A83A'); y+=38
    ing=recipe['ingredients']; mid=(len(ing)+1)//2
    f=sans(16)
    for col, arr in enumerate((ing[:mid],ing[mid:])):
        yy=y; x=26+col*245
        for name,amt in arr:
            txt=f'・{name}  {amt}'
            for line in wrap(d,txt,f,228)[:2]: d.text((x,yy),line,font=f,fill='#F0ECE3'); yy+=23
            yy+=3
    y=max(y+max(mid,len(ing)-mid)*29,1025)
    draw_panel(d,(26,y,516,y+150)); d.text((42,y+14),'美味しく作るポイント',font=serif(22),fill='#D8A83A')
    yy=y+50
    for p in recipe['points'][:3]:
        d.text((44,yy),'✓',font=sans(17),fill='#F1D400')
        for line in wrap(d,p,sans(15),438)[:2]: d.text((68,yy),line,font=sans(15),fill='#F0ECE3'); yy+=21
        yy+=3
    # pairing strip
    py=y+166; d.text((26,py),'おすすめの組み合わせ',font=serif(22),fill='#D8A83A'); py+=34
    thumb=92
    for i,(im,label) in enumerate(zip(pairings,recipe['pairings'][:4])):
        x=26+i*121; img.paste(fit(im,(thumb,thumb)),(x,py));
        lab=wrap(d,label,sans(13),108)[:2]; ty=py+97
        for line in lab: d.text((x,ty),line,font=sans(13),fill='#F0ECE3'); ty+=17
    # right column steps
    rowh=214; sy=22
    for i,(st,sim) in enumerate(zip(recipe['steps'],steps),1):
        top=sy+(i-1)*rowh; draw_panel(d,(rightx,top,850,top+rowh-8))
        d.text((555,top+12),f'{i:02d}',font=serif(30),fill='#D8A83A')
        d.text((606,top+17),st[0],font=serif(18),fill='#F4F0E8')
        # photo at right, text left below
        img.paste(fit(sim,(112,112)),(728,top+48))
        ty=top+55
        for line in wrap(d,st[1],sans(14),160)[:6]: d.text((555,ty),line,font=sans(14),fill='#E3DED5'); ty+=20
    tiptop=sy+6*rowh
    draw_panel(d,(rightx,tiptop,850,1518)); d.text((558,tiptop+14),'ひと工夫でさらに美味しく！',font=serif(17),fill='#D8A83A')
    ty=tiptop+48
    for line in wrap(d,recipe['extra'],sans(14),270)[:5]: d.text((558,ty),line,font=sans(14),fill='#F0ECE3'); ty+=20
    return img

def caption(no,dish,recipe):
    lines=[f'{dish}。保存して週末ごはんにどうぞ。','', '材料（2人前）']
    lines += [f'{n} … {a}' for n,a in recipe['ingredients']]
    lines += ['', '作り方']
    for i,(t,b) in enumerate(recipe['steps'],1): lines += [f'{i:02d} {t}',b]
    lines += ['', '美味しく作るポイント'] + [f'✅ {p}' for p in recipe['points']]
    lines += ['', f'ひと工夫：{recipe["extra"]}', '', '#ズルめし #簡単レシピ #ふたりごはん #おうちごはん #節約レシピ', '', f'【レシピ番号】{no}', f'【料理名】{dish}']
    return '\n'.join(lines)+'\n'

def qa(outdir,no,dish,recipe):
    p1=outdir/'slide_01_cover.jpg'; p2=outdir/'slide_02_recipe.jpg'; p3=outdir/'caption.txt'
    if not all(p.exists() and p.stat().st_size>10_000 for p in (p1,p2)): raise RuntimeError('QA: image missing/too small')
    if not p3.exists(): raise RuntimeError('QA: caption missing')
    for p in (p1,p2):
        with Image.open(p) as im:
            if im.size!=(W,H): raise RuntimeError(f'QA: wrong size {p} {im.size}')
    cap=p3.read_text(encoding='utf-8')
    if f'【レシピ番号】{no}' not in cap or f'【料理名】{dish}' not in cap: raise RuntimeError('QA: caption id mismatch')
    if len(recipe['steps'])!=6 or len(recipe['benefits'])!=3: raise RuntimeError('QA: schema mismatch')
    if any('DEMO' in x for x in cap.splitlines()): raise RuntimeError('QA: dummy content')
    return True

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--date'); args=ap.parse_args()
    ds=args.date or datetime.now().astimezone().date().isoformat()
    if ds not in SCHEDULE: raise SystemExit(f'予定表未登録: {ds}')
    no,dish,category=SCHEDULE[ds]; day=date.fromisoformat(ds)
    client=gemini_client(); recipe=gen_recipe(client,dish,category)
    # exact dish identity lock
    if no=='017':
        assert dish=='せせりアスパラレモンバター'
    hero=gen_image(client,photo_prompt(dish,recipe),'9:16')
    step_grid=gen_image(client,steps_prompt(dish,recipe),'3:4'); steps=split_grid(step_grid,3,2)[:6]
    pairing_grid=gen_image(client,pairing_prompt(recipe['pairings']),'1:1'); pairs=split_grid(pairing_grid,2,2)[:4]
    outdir=OUT/f'{ds}_{no}_{dish.replace("/","_")}' ; outdir.mkdir(parents=True,exist_ok=True)
    render_cover(day,recipe,hero).save(outdir/'slide_01_cover.jpg',quality=96,subsampling=0)
    render_card(day,recipe,hero,steps,pairs).save(outdir/'slide_02_recipe.jpg',quality=96,subsampling=0)
    (outdir/'caption.txt').write_text(caption(no,dish,recipe),encoding='utf-8')
    (outdir/'recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
    qa(outdir,no,dish,recipe)
    print(f'COMPLETE {ds} {no} {dish} {category} -> {outdir}')

if __name__=='__main__': main()
