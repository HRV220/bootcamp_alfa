from native_lib import *
import struct,hashlib

SRC=NIGHT/'output/Dota2_All_Cases_v2.pptx'
OUT=NIGHT/'output/Dota2_All_Cases_v2_images.pptx'
ASSETS=ROOT/'night/image'; media={}; mapping=[]
def picture(root,num,name,x,y,w,h,crop=(0,0,1,1)):
    data=(ASSETS/name).read_bytes(); iw,ih=struct.unpack('>II',data[16:24]); l,t,r,b=crop
    aspect=iw*(r-l)/(ih*(b-t)); ww=min(w,h*aspect); hh=ww/aspect
    tree=root.find('.//'+q(P,'spTree')); ident=max(int(n.get('id','0')) for n in root.findall('.//'+q(P,'cNvPr')))+1
    pic=sub(tree,P,'pic'); nv=sub(pic,P,'nvPicPr'); sub(nv,P,'cNvPr',{'id':str(ident),'name':name,'descr':'Оригинальное изображение из night/image'}); sub(nv,P,'cNvPicPr'); sub(nv,P,'nvPr')
    rid=f'rIdUserImage{ident}'; bf=sub(pic,P,'blipFill'); sub(bf,A,'blip',{q(R,'embed'):rid})
    if crop!=(0,0,1,1): sub(bf,A,'srcRect',{'l':str(round(l*100000)),'t':str(round(t*100000)),'r':str(round((1-r)*100000)),'b':str(round((1-b)*100000))})
    sub(sub(bf,A,'stretch'),A,'fillRect'); sp=sub(pic,P,'spPr'); xf(sp,x+(w-ww)/2,y+(h-hh)/2,ww,hh); sub(sub(sp,A,'prstGeom',{'prst':'rect'}),A,'avLst')
    target=f'user_image_{num}_{ident}.png'; media['ppt/media/'+target]=data
    mapping.append({'slide':num,'source':'night/image/'+name,'crop_fraction':crop,'sha256':hashlib.sha256(data).hexdigest()})
    return (rid,R+'/image','../media/'+target)

with zipfile.ZipFile(SRC) as z: parts={n:z.read(n) for n in z.namelist()}
for i in range(1,16):
    root=E.fromstring(parts[f'ppt/slides/slide{i}.xml']); relpath=f'ppt/slides/_rels/slide{i}.xml.rels'; rel=E.fromstring(parts[relpath])
    for shape in root.findall('.//'+q(P,'sp')):
        texts=shape.findall('.//'+q(A,'t')); text=''.join(n.text or '' for n in texts)
        if text==f'{i:02}':
            tx=shape.find('./'+q(P,'spPr')+'/'+q(A,'xfrm')); tx.find(q(A,'off')).set('x',emu(934)); tx.find(q(A,'off')).set('y',emu(508)); tx.find(q(A,'ext')).set('cx',emu(22))
        if i==1 and text=='Анализ данных Dota 2':
            shape.find('./'+q(P,'spPr')+'/'+q(A,'xfrm')+'/'+q(A,'ext')).set('cx',emu(570))
    args=('Alfa-Buduschee_01_krasny_1.png',670,20,250,88) if i==1 else ('Alfa-Buduschee_01_krasny_1.png',842,25,88,34)
    entries=[picture(root,i,*args)]
    if i==1: entries.append(picture(root,i,'Alfa_Bank_tabletka_belaya_1.png',770,440,150,48))
    for rid,typ,target in entries: E.SubElement(rel,q(REL,'Relationship'),{'Id':rid,'Type':typ,'Target':target})
    parts[f'ppt/slides/slide{i}.xml']=xml(root); E.register_namespace('',REL); parts[relpath]=xml(rel)

# The first 15 slides remain the talk. Detailed source figures form an appendix.
appendix=[
('SQL: матчи, участники и справочники','mermaid-diagram-2026-11-14-194153.png',(0,0,1,.52),'Фрагмент ER-схемы SQL\n\nМатч: match_id\nУчастник: match_id + player_slot\nПредмет: item_id\nГерой: hero_id\n\nСвязь героя в исходной схеме\nпомечена pending.'),
('SQL: события покупок','mermaid-diagram-2026-11-14-194153.png',(0,.48,1,1),'Фрагмент ER-схемы SQL\n\nСобытие покупки: id\nПривязка: match_id + account_id\nПредмет: itemid = item_id\n\nФактический dom_buyers использует\nROW_NUMBER для повторов аккаунта.\nОднозначность требует проверки.'),
('ML: ключ статистики участников','mermaid-diagram-2026-11-14-194146.png',(.10,.52,.45,.73),'Фрагмент физической модели ML\n\nКлюч наблюдения:\nmatch_id + player_slot\n\nАккаунт не является ключом\nнаблюдения игрока в матче.\nNotebook читает match_players\nнепосредственно из PostgreSQL.'),
('ML: отдельный CSV кандидатов','mermaid-diagram-2026-11-14-194146.png',(.64,0,1,.216),'Фрагмент CSV_SMURF_PLAYERS\n\n87 наблюдений, 6 аккаунтов\nВсе метки smurf = 1\n\nЭто отдельный набор находок.\nОн не является test-набором\nприведённых метрик CatBoost.\nНа схеме показана часть полей.'),
('LLM: покупки и убийства','mermaid-diagram-2026-11-14-194411.png',(0,0,.36,1),'Фрагмент модели событий LLM\n\nПокупки связаны со справочником\nпредметов по itemid.\n\nСемантика attacker / target\nна схеме требует проверки.\nТекущий notebook использует\nограниченный набор фактов.'),
('LLM: матчи, участники и золото','mermaid-diagram-2026-11-14-194411.png',(.35,0,.75,1),'Фрагмент ER-схемы LLM\n\nМатч, статистика участников\nи события золота.\n\nНаличие поля в общей схеме\nне означает, что оно попало\nво вход текущего обзора.\nНапример, исход матча не извлечён.'),
('Общая модель: матчи и события','mermaid-diagram-2026-11-14-203234.png',(.26,0,.62,.44),'Фрагмент общей модели\n\nСвязи матча с событиями\nразных типов.\n\nПолная схема связывает все кейсы,\nно не подтверждает общий snapshot.\nЛогические связи не являются\nфизическими ограничениями Iceberg.')
]
types=E.fromstring(parts['[Content_Types].xml']); pres=E.fromstring(parts['ppt/presentation.xml']); ids=pres.find(q(P,'sldIdLst')); rel=E.fromstring(parts['ppt/_rels/presentation.xml.rels'])
for num,(title,name,crop,body) in enumerate(appendix,16):
    s=Slide(num,title); s.footer('Приложение. Оригинальная схема: night/image/'+name)
    entries=[picture(s.root,num,name,40,101,600,391,crop),picture(s.root,num,'Alfa-Buduschee_01_krasny_1.png',842,25,88,34)]
    s.text(668,112,252,350,body,14.5,WHITE)
    # Move folio away from the logo.
    for sh in s.root.findall('.//'+q(P,'sp')):
        if ''.join(t.text or '' for t in sh.findall('.//'+q(A,'t')))==f'{num:02}':
            t=sh.find('./'+q(P,'spPr')+'/'+q(A,'xfrm')); t.find(q(A,'off')).set('x',emu(934)); t.find(q(A,'off')).set('y',emu(508)); t.find(q(A,'ext')).set('cx',emu(22))
    rid=f'rIdImageAppendixSlide{num}'; sub(ids,P,'sldId',{'id':str(1000+num),q(R,'id'):rid}); E.SubElement(rel,q(REL,'Relationship'),{'Id':rid,'Type':R+'/slide','Target':f'slides/slide{num}.xml'})
    parts[f'ppt/slides/slide{num}.xml']=xml(s.root)
    parts[f'ppt/slides/_rels/slide{num}.xml.rels']=relationships([('rIdLayout',R+'/slideLayout','../slideLayouts/slideLayout1.xml'),('rIdNotes',R+'/notesSlide',f'../notesSlides/notesSlide{num}.xml')]+entries)
    parts[f'ppt/notesSlides/notesSlide{num}.xml']=xml(notes('Источник изображения: night/image/'+name+'. На слайде показан увеличенный фрагмент оригинального PNG без перерисовки. Полное изображение сохранено внутри PPTX и доступно через сброс обрезки. Пояснение: '+body.replace('\n',' ')))
    parts[f'ppt/notesSlides/_rels/notesSlide{num}.xml.rels']=relationships([('rIdSlide',R+'/slide',f'../slides/slide{num}.xml')])
    for part,typ in [('slides/slide','slide'),('notesSlides/notesSlide','notesSlide')]: E.SubElement(types,q(CT,'Override'),{'PartName':f'/ppt/{part}{num}.xml','ContentType':f'application/vnd.openxmlformats-officedocument.presentationml.{typ}+xml'})
parts['ppt/presentation.xml']=xml(pres); E.register_namespace('',REL); parts['ppt/_rels/presentation.xml.rels']=xml(rel); E.register_namespace('',CT); parts['[Content_Types].xml']=xml(types); parts.update(media)
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
    for n,v in parts.items(): z.writestr(n,v)
(NIGHT/'qa/images_mapping.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
print(OUT)
print([(p.name,struct.unpack('>II',p.read_bytes()[16:24])) for p in ASSETS.glob('*.png')])
