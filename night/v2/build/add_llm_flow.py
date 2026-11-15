from native_lib import *
import struct
SOURCE=NIGHT/'output/Dota2_All_Cases_v2_simple.pptx'
with zipfile.ZipFile(SOURCE) as z: parts={n:z.read(n) for n in z.namelist()}
media={}
def pic(s,path,x,y,w,h):
    data=(ROOT/path).read_bytes(); iw,ih=struct.unpack('>II',data[16:24]); scale=min(w/iw,h/ih); ww,hh=iw*scale,ih*scale
    p=sub(s.tree,P,'pic'); nv=sub(p,P,'nvPicPr'); sub(nv,P,'cNvPr',{'id':str(s.next),'name':path}); s.next+=1; sub(nv,P,'cNvPicPr'); sub(nv,P,'nvPr'); rid=f'rIdFlowImage{s.next}'; bf=sub(p,P,'blipFill'); sub(bf,A,'blip',{q(R,'embed'):rid}); sub(sub(bf,A,'stretch'),A,'fillRect'); sp=sub(p,P,'spPr'); xf(sp,x+(w-ww)/2,y+(h-hh)/2,ww,hh); sub(sub(sp,A,'prstGeom',{'prst':'rect'}),A,'avLst'); name=f'llm_flow_{s.num}_{s.next}.png'; media['ppt/media/'+name]=data; s.rels.append((rid,R+'/image','../media/'+name))
def style(s):
    pic(s,'night/image/Alfa-Buduschee_01_krasny_1.png',842,25,88,34)
    for sh in s.root.findall('.//'+q(P,'sp')):
        if ''.join(t.text or '' for t in sh.findall('.//'+q(A,'t')))==f'{s.num:02}':
            tr=sh.find('./'+q(P,'spPr')+'/'+q(A,'xfrm')); tr.find(q(A,'off')).set('x',emu(934)); tr.find(q(A,'off')).set('y',emu(508)); tr.find(q(A,'ext')).set('cx',emu(22))

s=Slide(11,'Как данные превращаются в обзор матча')
s.text(40,91,880,42,'Один ноутбук Jupyter: подготовка данных и два вызова языковой модели',17,WHITE)
for x,w,t,b in [(40,170,'Озеро данных','Таблицы матчей,\nсобытий, героев\nи предметов'),(235,160,'Подготовка','Выбрали матч,\nсвязали записи\nи отсортировали\nсобытия по времени'),(420,230,'Первый вызов модели','Вход: факты о событиях\n\nВыход: короткое описание\nкаждого события'),(675,245,'Второй вызов модели','Вход: описания событий\n\nВыход: связный обзор\nвсего матча')]: s.box(x,155,w,160,t,b,13.5)
for a,b in [(210,235),(395,420),(650,675)]: s.line(a,231,b,231,WHITE,True)
s.text(40,354,880,99,'Сначала модель объясняет отдельные эпизоды: кто, что и когда сделал.\nЗатем второй вызов объединяет эти описания в рассказ о матче.\nНа примере одного матча обработали 181 событие.',18,WHITE)
s.footer('По коду case3.ipynb. В обоих вызовах указана одна модель: GPT-5.4 nano')
s.notes='Источник: task/case3/case3.ipynb, кодовые клетки 1,2,3. Фактические входы Spark SQL: lakehouse.raw.mongo__kill_events, tower_death_events, gold_events, buyback_events, purchase_events, streak_events; справочники raw.pg__items, pg__heroes и участники pg__match_players. pg__matches непосредственно в notebook не извлекается, поэтому победитель и длительность не попадают в payload. Подготовка: фильтры, обогащение и сортировка clean_events, match_payload с match_id и массивом events. Первый client.chat.completions.create превращает факты в описания событий с event_id. Второй вызов получает event_id/type/time и сгенерированное описание, собирает summary. Используется zip(source_events,first_events), что требует проверки соответствия. Оба вызова настроены на openai/gpt-5.4-nano. Схема описывает текущую реализацию, не гарантирует точность текста. Ноутбук и API при подготовке слайдов не запускались.'
# Correct the first node to actual notebook inputs, not nonexistent matches SELECT.
for sh in s.root.findall('.//'+q(P,'sp')):
    for t in sh.findall('.//'+q(A,'t')):
        if t.text=='Таблицы матчей,': t.text='События матча,'
        elif t.text=='событий, героев': t.text='игроки, герои'
        elif t.text=='и предметов': t.text='и предметы'
flow=s; style(flow)

s=Slide(12,'Пример работы в ноутбуке')
s.text(40,93,282,31,'1. Исходные события',17,LIME,True)
pic(s,'task/case3/1.png',40,134,282,350)
s.text(364,93,556,31,'2. Первый вызов: описания событий',17,LIME,True)
pic(s,'task/case3/2.png',364,138,556,50)
s.text(364,207,556,80,'Например: на 0:15 Monkey King убил Dragon Knight,\nполучив 536 золота и 66 опыта.',16.5,WHITE)
s.text(364,304,556,31,'3. Второй вызов: общий обзор',17,LIME,True)
pic(s,'task/case3/3.png',364,350,556,78)
s.text(364,445,556,42,'Из отдельных описаний получился связный текст о матче.',16.5,WHITE)
s.footer('Оригинальные снимки 1.png, 2.png и 3.png из папки task/case3')
s.notes='Пользовательские исходные скриншоты task/case3/1.png,2.png,3.png встроены целиком, без перерисовки и без обрезки. Первый: JSON match9045752693, первое событие time15 Monkey King→Dragon Knight gold536 xp66. Второй: первый ответ с описанием события «На 0:15 Monkey King убил Dragon Knight, получив 536 золота и 66 опыта.» Третий: итоговый текст обзора. Скриншоты 2 и3 исходно узкие и часть длинных строк за границами интерфейса; это предоставленные снимки, не полная выгрузка. Крупные подписи передают назначение этапов. На следующем слайде сохранены результаты проверки ошибок обзора; наличие скриншота не доказывает его фактическую точность.'
screens=s; style(screens)

types=E.fromstring(parts['[Content_Types].xml']); pres=E.fromstring(parts['ppt/presentation.xml']); ids=pres.find(q(P,'sldIdLst')); ids.clear(); rel=E.fromstring(parts['ppt/_rels/presentation.xml.rels'])
for e in list(rel):
    if e.get('Type','').endswith('/slide'): rel.remove(e)
old=parts.copy()
for k in list(parts):
    if k.startswith(('ppt/slides/','ppt/notesSlides/')): del parts[k]
for e in list(types):
    if e.get('PartName','').startswith(('/ppt/slides/','/ppt/notesSlides/')): types.remove(e)
for num in range(1,17):
    rid=f'rIdLlmFlowSlide{num}'; sub(ids,P,'sldId',{'id':str(255+num),q(R,'id'):rid}); E.SubElement(rel,q(REL,'Relationship'),{'Id':rid,'Type':R+'/slide','Target':f'slides/slide{num}.xml'})
    if num in [11,12]:
        sl=flow if num==11 else screens; root=sl.root; nbytes=xml(notes(sl.notes)); extra=sl.rels
        rb=relationships([('rIdLayout',R+'/slideLayout','../slideLayouts/slideLayout1.xml'),('rIdNotes',R+'/notesSlide',f'../notesSlides/notesSlide{num}.xml')]+extra)
    else:
        orig=num if num<11 else num-1
        root=E.fromstring(old[f'ppt/slides/slide{orig}.xml']); nbytes=old[f'ppt/notesSlides/notesSlide{orig}.xml']; rr=E.fromstring(old[f'ppt/slides/_rels/slide{orig}.xml.rels'])
        for e in rr:
            if e.get('Type','').endswith('/notesSlide'): e.set('Target',f'../notesSlides/notesSlide{num}.xml')
        E.register_namespace('',REL); rb=xml(rr)
        for sh in root.findall('.//'+q(P,'sp')):
            ts=sh.findall('.//'+q(A,'t'))
            if ''.join(t.text or '' for t in ts)==f'{orig:02}': ts[0].text=f'{num:02}'
    parts[f'ppt/slides/slide{num}.xml']=xml(root); parts[f'ppt/slides/_rels/slide{num}.xml.rels']=rb
    parts[f'ppt/notesSlides/notesSlide{num}.xml']=nbytes; parts[f'ppt/notesSlides/_rels/notesSlide{num}.xml.rels']=relationships([('rIdSlide',R+'/slide',f'../slides/slide{num}.xml')])
    for stem,typ in [('slides/slide','slide'),('notesSlides/notesSlide','notesSlide')]: E.SubElement(types,q(CT,'Override'),{'PartName':f'/ppt/{stem}{num}.xml','ContentType':f'application/vnd.openxmlformats-officedocument.presentationml.{typ}+xml'})
parts.update(media); parts['ppt/presentation.xml']=xml(pres); E.register_namespace('',REL); parts['ppt/_rels/presentation.xml.rels']=xml(rel); E.register_namespace('',CT); parts['[Content_Types].xml']=xml(types)
out=NIGHT/'output/Dota2_All_Cases_v2_llm_flow.pptx'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for n,v in parts.items(): z.writestr(n,v)
print(out)
