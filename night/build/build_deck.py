"""Native OOXML authoring fallback: the supplied @oai/artifact-tool runtime is absent.
Uses the supplied template package, preserves its 11-slide sequence and canvas.
No python-pptx or external dependencies. All output paths are below night.
"""
from pathlib import Path
import xml.etree.ElementTree as E
import zipfile, json, copy, html, io

ROOT=Path(__file__).resolve().parents[2]
NIGHT=ROOT/'night'
P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
C='http://schemas.openxmlformats.org/drawingml/2006/chart'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
for k,v in [('p',P),('a',A),('r',R),('c',C)]: E.register_namespace(k,v)
def q(n,t): return '{'+n+'}'+t
def sub(p,n,t,attrs=None): return E.SubElement(p,q(n,t),attrs or {})
def emu(v): return str(round(v*12700))
BLUE='2B73FE'; RED='EF3124'; PURPLE='6F2BFE'; INK='0F1115'; GRAY='EEF2F8'; WHITE='FFFFFF'; LIME='B5EE00'
FONT='Arial'
def fill(p,color):
    if color: sub(sub(p,A,'solidFill'),A,'srgbClr',{'val':color})
    else: sub(p,A,'noFill')
def xf(p,x,y,w,h):
    t=sub(p,A,'xfrm'); sub(t,A,'off',{'x':emu(x),'y':emu(y)}); sub(t,A,'ext',{'cx':emu(w),'cy':emu(h)})
def paragraph(parent,text,size=15,color=INK,bold=False,align='l',space=6):
    p=sub(parent,A,'p'); pr=sub(p,A,'pPr',{'algn':align}); sub(pr,A,'lnSpc'); pr.remove(pr[-1]); sub(sub(pr,A,'lnSpc'),A,'spcPct',{'val':'108000'}); sub(sub(pr,A,'spcAft'),A,'spcPts',{'val':str(round(space*100))}); sub(pr,A,'buNone')
    r=sub(p,A,'r'); rp=sub(r,A,'rPr',{'lang':'ru-RU','sz':str(round(size*100)),'b':'1' if bold else '0'}); fill(rp,color)
    for script in ['latin','ea','cs']: sub(rp,A,script,{'typeface':FONT})
    sub(r,A,'t').text=text
    sub(p,A,'endParaRPr',{'lang':'ru-RU','sz':str(round(size*100))})
    return p

class Slide:
    def __init__(self,num,title,bg=BLUE):
        self.num=num; self.next=2; self.rels=[]; self.notes=''; self.title=title
        self.root=E.Element(q(P,'sld')); cs=sub(self.root,P,'cSld',{'name':title}); bgp=sub(sub(cs,P,'bg'),P,'bgPr'); fill(bgp,bg); sub(bgp,A,'effectLst')
        self.tree=sub(cs,P,'spTree'); nv=sub(self.tree,P,'nvGrpSpPr'); sub(nv,P,'cNvPr',{'id':'1','name':''}); sub(nv,P,'cNvGrpSpPr'); sub(nv,P,'nvPr'); gp=sub(self.tree,P,'grpSpPr'); t=sub(gp,A,'xfrm')
        for name,attrs in [('off',{'x':'0','y':'0'}),('ext',{'cx':'0','cy':'0'}),('chOff',{'x':'0','y':'0'}),('chExt',{'cx':'0','cy':'0'})]: sub(t,A,name,attrs)
        sub(sub(self.root,P,'clrMapOvr'),A,'masterClrMapping')
        self.text(40,23,790,52,title,30,WHITE,True)
        self.text(888,25,40,30,f'{num:02}',13,WHITE,False,'r')
    def shape(self,name,x,y,w,h,bg=None,line=None,geom='rect'):
        s=sub(self.tree,P,'sp'); nv=sub(s,P,'nvSpPr'); sub(nv,P,'cNvPr',{'id':str(self.next),'name':name}); self.next+=1; sub(nv,P,'cNvSpPr'); sub(nv,P,'nvPr'); pr=sub(s,P,'spPr'); xf(pr,x,y,w,h); sub(sub(pr,A,'prstGeom',{'prst':geom}),A,'avLst'); fill(pr,bg); ln=sub(pr,A,'ln',{'w':'12700'}); fill(ln,line)
        return s
    def text(self,x,y,w,h,text,size=15,color=WHITE,bold=False,align='l',bg=None,line=None,pad=0):
        s=self.shape(text[:65],x,y,w,h,bg,line); tx=sub(s,P,'txBody'); sub(tx,A,'bodyPr',{'wrap':'square','lIns':emu(pad),'rIns':emu(pad),'tIns':emu(pad),'bIns':emu(pad),'anchor':'t'}); sub(tx,A,'lstStyle')
        for line_ in str(text).split('\n'): paragraph(tx,line_,size,color,bold,align)
        return s
    def box(self,x,y,w,h,title,body,size=14):
        return self.text(x,y,w,h,title+'\n'+body,size,INK,False,bg=WHITE,pad=12)
    def line(self,x1,y1,x2,y2,color=WHITE,arrow=False):
        s=sub(self.tree,P,'cxnSp'); nv=sub(s,P,'nvCxnSpPr'); sub(nv,P,'cNvPr',{'id':str(self.next),'name':'Связь данных'}); self.next+=1; sub(nv,P,'cNvCxnSpPr'); sub(nv,P,'nvPr'); sp=sub(s,P,'spPr'); xf(sp,min(x1,x2),min(y1,y2),abs(x2-x1),abs(y2-y1)); sub(sub(sp,A,'prstGeom',{'prst':'line'}),A,'avLst'); ln=sub(sp,A,'ln',{'w':'19050'}); fill(ln,color)
        if arrow: sub(ln,A,'tailEnd',{'type':'triangle','w':'sm','len':'sm'})
    def table(self,x,y,width,widths,rows,heights,size=12):
        frame=sub(self.tree,P,'graphicFrame'); nv=sub(frame,P,'nvGraphicFramePr'); sub(nv,P,'cNvPr',{'id':str(self.next),'name':'Редактируемая таблица'}); self.next+=1; sub(nv,P,'cNvGraphicFramePr'); sub(nv,P,'nvPr'); t=sub(frame,P,'xfrm'); sub(t,A,'off',{'x':emu(x),'y':emu(y)}); sub(t,A,'ext',{'cx':emu(width),'cy':emu(sum(heights))})
        gd=sub(sub(frame,A,'graphic'),A,'graphicData',{'uri':'http://schemas.openxmlformats.org/drawingml/2006/table'}); tab=sub(gd,A,'tbl'); sub(tab,A,'tblPr',{'firstRow':'1','bandRow':'0'}); grid=sub(tab,A,'tblGrid')
        for v in widths: sub(grid,A,'gridCol',{'w':emu(v)})
        for ri,row in enumerate(rows):
            tr=sub(tab,A,'tr',{'h':emu(heights[ri])})
            for ci,content in enumerate(row):
                tc=sub(tr,A,'tc'); tx=sub(tc,A,'txBody'); sub(tx,A,'bodyPr'); sub(tx,A,'lstStyle')
                for line_ in content.split('\n'): paragraph(tx,line_,size,WHITE if ri==0 else INK,ri==0,space=2)
                pr=sub(tc,A,'tcPr',{'marL':emu(8),'marR':emu(8),'marT':emu(6),'marB':emu(4),'anchor':'t'})
                for tag in ['lnL','lnR','lnT','lnB']:
                    ln=sub(pr,A,tag,{'w':'6350'}); fill(ln,BLUE)
                fill(pr,PURPLE if ri==0 else WHITE)
        return frame
    def placeholder(self,x,y,w,h,label,detail):
        self.text(x,y,w,h,label+'\n'+detail,12,INK,False,'ctr',GRAY,PURPLE,12)
    def footer(self,text): self.text(40,506,880,24,text,9.5,WHITE)
    def chart(self,x,y,w,h,idx):
        f=sub(self.tree,P,'graphicFrame'); nv=sub(f,P,'nvGraphicFramePr'); sub(nv,P,'cNvPr',{'id':str(self.next),'name':'Матчи по аккаунтам, CSV'}); self.next+=1; sub(nv,P,'cNvGraphicFramePr'); sub(nv,P,'nvPr'); t=sub(f,P,'xfrm'); sub(t,A,'off',{'x':emu(x),'y':emu(y)}); sub(t,A,'ext',{'cx':emu(w),'cy':emu(h)})
        gd=sub(sub(f,A,'graphic'),A,'graphicData',{'uri':C}); sub(gd,C,'chart',{q(R,'id'):'rIdChart'}); self.rels.append(('rIdChart',R+'/chart',f'../charts/chart{idx}.xml'))

slides=[]
def new(title):
    s=Slide(len(slides)+1,title); slides.append(s); return s

s=new('Анализ данных Dota 2')
s.text(40,111,870,127,'Доминатор и винрейт\nПоиск аномальных профилей',36,WHITE,True)
s.text(42,269,790,48,'SQL / аналитика и ML №18 «Обнаружение смурфов»',19,WHITE)
s.text(42,333,840,120,'Роман Охопков — DE     Сергей Голдаев — SA\nАнтон Кузьмин — PA     Роман Хожанец — BA',17,WHITE)
s.footer('Буткэмп по дата-инженерии, Томск, 12–15 ноября 2026. Срез материалов: 14.11.2026')
s.notes='Два кейса текущей защиты: SQL про Helm of the Dominator и ML №18. Название команды в team.md не задано, поэтому не придумано. Состав и роли: requirements/team.md. Третий кейс LLM №24 из selected_cases.md не входит в текущую защиту по уточнению пользователя «оба кейса».'

s=new('Задача')
s.text(40,106,880,94,'Игроку нужна проверяемая связь времени покупки Доминатора с исходом матча, чтобы обсуждать тайминг на основе данных.',23,WHITE)
s.text(40,224,880,94,'Аналитику матчмейкинга нужен список нетипичных профилей для ручной проверки, чтобы направлять внимание на подозрительные случаи.',23,WHITE)
s.text(40,363,880,95,'Результат: воспроизводимый расчёт разницы винрейтов и обоснованный список кандидатов. Аномальность сама по себе не доказывает смурфинг.',18,WHITE)
s.footer('Заказчики и сценарии использования — рабочая постановка команды. Источник: task/selected_cases.md')
s.notes='Бизнес-сценарии сформулированы на основе целей кейсов, это не подтверждённые интервью с внешним заказчиком. Выгода первого кейса — корректное сравнение таймингов, второго — приоритизация ручной проверки. Причинный эффект покупки и автоматическое наказание игроков не заявляются.'

s=new('Бизнес-вопрос и гипотезы')
s.table(40,103,880,[342,245,293],[
 ['Гипотеза','Метрика и правило','Необходимые данные'],
 ['SQL: если первая покупка раньше, то винрейт выше, поскольку тайминг связан с ходом матча','ΔWR = WRранние − WRпоздние\nЦель: не менее +3 п.п.','itemid=164, первое время, исход\nРанние: t ≤ медианы среза'],
 ['ML: если профиль нетипичен среди peers, то score выделит кандидата, поскольку показатели отличаются от группы','Качество top-K по ручной разметке\nСравнение с пороговым baseline','История кандидатов и контроля\nKDA, GPM, XPM, урон/мин'],
 ['ML: если учесть роль и уровень матча, то ложных тревог станет меньше, поскольку ожидаемые показатели различаются','Доля ложных тревог при одном K\nСравнение моделей с/без peers','Роль, ранг или иной уровень\nНезависимая оценка кандидатов']
 ],[34,90,90,90],12.5)
s.text(40,431,880,55,'Peers — сопоставимые игроки. Порог медианы фиксируется до сравнения винрейтов. Методики и пороги ML ещё требуют согласования.',14,WHITE)
s.footer('Гипотезы: task/selected_cases.md и task/case1/case_definition.md. ML-метрики — предлагаемый план')
s.notes='SQL: единица анализа — покупатель в матче, не событие покупки. Точная медиана очищенной выборки, ранние <= медианы, поздние >. +3 п.п. — целевой эффект, не полученный результат. SQL-гипотеза ассоциативная. ML peers, оценка top-K и сравнение ложных тревог являются предложением, а не выполненным экспериментом.'

s=new('Данные и связи')
# Required editable ER diagram with readable keys.
s.box(40,104,245,111,'PostgreSQL: matches','PK match_id\nstart_time, duration, radiant_win',13)
s.box(40,280,245,122,'PostgreSQL: match_players','PK (match_id, player_slot)\naccount_id, hero_id, rank, win',13)
s.box(363,177,294,144,'MongoDB: purchase_events','PK id\nmatch_id, steam_account_id\nitemid, time (сек. от начала)',13)
s.box(716,104,204,100,'PostgreSQL: items','PK item_id\nДоминатор: 164',13)
s.box(716,263,204,139,'CSV кандидатов ML','87 строк, 6 аккаунтов\nКлюч: match_id + slot\n7 пустых полей, контроля нет',13)
s.line(162,215,162,280,WHITE,True); s.text(170,233,130,30,'1 : N, match_id',10,WHITE)
s.line(285,151,510,151); s.line(510,151,510,177,WHITE,True); s.text(310,126,180,23,'match_id, 0..1 совпадение',10,WHITE)
s.line(285,341,510,341); s.line(510,321,510,341); s.text(307,347,365,40,'match_id + account_id = steam_account_id\nДопуск: ровно один участник на покупку',10,WHITE)
s.line(657,227,818,227); s.line(818,204,818,227); s.text(683,206,95,20,'itemid = item_id',10,WHITE)
s.text(40,429,880,60,'Целевые правила: боты account=0, неразрешённые связи и пары с >2 событиями — вне анализа. NULL ранга сохраняем. Ошибки остаются в диагностике до первой покупки.',14,WHITE)
s.footer('ER — логическая модель. Наличие таблиц и ограничения уникальности проверяются на фиксированном снимке')
s.notes='Источники: requirements/Источники. Описание полей таблиц.md; task/case1/data_model.md; task/case2/smurf_players.csv. Связи покупок показаны как логические, наличие совпадений не гарантировано. Число соответствий проверяется до JOIN: нельзя восстанавливать сторону покупателя только по match_id. Анонимный ID 4294967295 допустим только при однозначной привязке к участнику. CSV не связан с SQL-срезом доказанным периодом. Полностью пустые поля: rank, calibration, rank_known, tier, kda_c, farm_pos, perf_z. heroes — необязательный справочник, отсутствие имени не удаляет наблюдение. Предлагаемая доработка: quarantining целой пары при любом невалидном событии до min(time).'

s=new('Архитектура и паспорта витрин')
s.text(40,88,880,30,'Целевая схема: Airflow управляет SQL, Spark обрабатывает, Iceberg хранит таблицы в MinIO',14,WHITE)
for x,w,title,body in [(40,150,'Источники','PostgreSQL\nMongoDB, CSV'),(218,176,'RAW','Снимки входов\nметки загрузок'),(422,196,'STAGE','Покупки + DQ\nпрофили игроков'),(646,174,'MART','Первые покупки\nΔWR, кандидаты')]: s.box(x,137,w,91,title,body,12.5)
for x1,x2 in [(190,218),(394,422),(618,646)]: s.line(x1,182,x2,182,WHITE,True)
s.box(842,137,78,91,'Trino','Superset',11)
s.line(820,182,842,182,WHITE,True)
s.text(40,244,880,33,'Lineage: purchases + matches + players → первые покупки → ΔWR → Trino → Superset',13,WHITE)
s.text(40,276,880,25,'ML: CSV / история peers → профиль игрока → score кандидатов → Trino → Superset (проект)',12,WHITE)
s.table(40,319,880,[242,140,152,148,198],[
 ['Витрина / гранулярность','SLA*','Обновление','Объём','Хранение'],
 ['dominator_first_purchase\nпокупатель в матче','≤30 мин после\nснимка*','Раз в час\nпри изменении','После DQ\nпока неизвестен','Срез 14–15.10\nдо защиты +30 дней'],
 ['dominator_winrate\nодна строка на срез','После первой\nвитрины*','После её\nпересборки','1 строка\nпо проекту','Снимки расчётов\nдо защиты +30 дней'],
 ['candidate_profile*\nаккаунт / окно','≤1 часа после\nприёма файла*','Новый CSV /\nокно истории*','Вход: 87 строк\nвыход: 6 профилей**','До защиты +30 дней*']
 ],[28,48,48,48],10.5)
s.footer('* Проектные параметры, не измеренный SLA. ** Локальные агрегаты CSV. SQL-частота и хранение — требования')
s.notes='Физическая целевая схема: PostgreSQL/MongoDB → Airflow → Spark → Iceberg/MinIO (RAW/STAGE/MART) → Trino → Superset. Lineage SQL: raw.mongo__purchase_events + raw.pg__matches + raw.pg__match_players + raw.pg__items → stage.case1_dominator_purchase_events → stage.case1_dominator_first_purchase → mart.case1_dominator_first_purchase → mart.case1_dominator_winrate → графики тайминга и ΔWR. Имена STAGE целевой версии взяты из data_model.md, наличие именно этих объектов надо сверить с кластером, поскольку текущие stages/*.md используют иные имена. ML: CSV → player-match features → profile account/window → score (проект), текущая локальная сводка не является ML-витриной. Предложенный SLA требует измерения: готовый снимок+30 минут, для ML файл+1 час; не гарантия выполнения. SQL хранение и часовой пересчёт — требования паспорта. Полная замена таблиц, согласованные snapshot/run_id, проверки до публикации.'

s=new('ETL и контроль выполнения')
s.text(40,86,880,40,'SQL в UI → проверка и описание таблицы → сохранение → автоматический DAG → запуск',14,WHITE)
s.placeholder(40,139,424,105,'Место для реального скриншота SQL / STAGE','Добавить имя таблицы, время запуска и число строк')
s.placeholder(496,139,424,105,'Место для реального скриншота Airflow DAG','Добавить run_id, зависимости и статус задач')
s.table(40,266,880,[171,273,239,197],[
 ['Поток','Вход и выход','Правило обновления','Статус / расписание'],
 ['События + DQ','RAW покупки + матч + участник\n→ STAGE события','Снимок целиком\nвсе ошибки сохраняем','Кандидат SQL\nраз в час — требование'],
 ['Первая покупка','STAGE события\n→ STAGE первая покупка','MIN только по чистой паре\nодин snapshot_id','Кандидат SQL\nпосле событий'],
 ['Метрики SQL','Первая покупка → MART\nмедиана, группы, ΔWR','Полный пересчёт на том же\nочищенном срезе','SQL подготовлен\nзапуск не подтверждён'],
 ['Профиль ML','CSV → локальные агрегаты\n87 строк → 6 профилей','Новый файл по SHA256\nконтроль ключей и формул','Локальный расчёт готов\nDAG не подтверждён']
 ],[28,38,38,38,38],10.7)
s.text(40,462,880,34,'Контроль: ключи и row count, DQ, один снимок. Сбой: Log → причина → Clear / Rerun → сверка.',12,WHITE)
s.footer('STAGE созданы со слов команды. Соответствие этим потокам, число DAG, run_id и расписание не проверены')
s.notes='Скриншоты оставлены по разрешению пользователя, они не имитируют интерфейс. Пользователь сообщил: «есть созданные stage». Это подтверждение наличия STAGE вообще со слов команды, но не наличия именно двух кандидатных потоков таблицы. Существующие task/case1/stages используют matches_fixed, match_players, purchase_events. Предлагаемые night/analysis/case1_sql сохраняют DQ до MIN и требуют отдельной проверки/создания в тестовой зоне. SQL пишется в UI, DAG создаётся платформой, команда проверяет статус/логи/перезапуск. Предложение: фиксированный срез вместо непроверенного инкремента. Для RAW incremental watermark src_modified_stamp можно вводить только после проверки поздних изменений. Идемпотентность: повторная полная сборка из того же snapshot даёт тот же набор бизнес-строк, техническая метка запуска может отличаться. Обнаружены расхождения: matches_fixed vs stage.matches, loaded_at vs sys_insert_stamp, отбрасывание ошибочных событий перед MIN. Они требуют проверки в кластере. Экран SQL и DAG следует вставить без уменьшения до нечитаемости. Таблица потоков описывает логические потоки, не подтверждённый счётчик DAG.'

s=new('Аналитика: проверка гипотез')
s.table(40,103,880,[171,305,190,214],[
 ['Гипотеза','Метод проверки','Текущий результат','Ограничения'],
 ['SQL: ранняя покупка\nи винрейт','Точная медиана → ΔWR\n95% ДИ, bootstrap по match_id\nс повторной оценкой медианы*','Недостаточно данных\nВыгрузки MART нет','Зависимость покупателей\nв одном матче\nПолнота истории неизвестна'],
 ['ML: профиль\nотличается от peers','Пороговый baseline + Isolation Forest*\nОценка top-K вручную\nholdout по аккаунтам и времени*','Профилирование готово\nМодель не оценена','Все метки smurf=1\nнет контрольной группы\n87 строк ≠ 87 игроков'],
 ['ML: peers уменьшают\nложные тревоги','Одинаковый K, одна разметка*\nСравнить с/без роли и уровня\nне смешивать train и test*','Недостаточно данных\nРоль и ранг не заданы','rank и tier пусты\nнет проверенных peers\nнет независимых меток']
 ],[34,99,99,99],12)
s.text(40,453,880,40,'Выбросы SQL: неверное время и >2 событий — в DQ. Экстремальные ML-показатели сначала проверяем.',13,WHITE)
s.footer('* Предлагаемый протокол. Статзначимость, причинный эффект и качество ML пока не установлены')
s.notes='Для SQL до проверки фиксируем период [2026-10-14 00:00 UTC, 2026-10-16 00:00 UTC), фильтры режима/лобби и снимок. Точная медиана по одному покупателю в матче до сравнения WR. ΔWR выражен в процентных пунктах. Bootstrap следует кластеризовать по match_id, потому что покупатели одного матча зависимы. В каждой реплике повторяем оценку медианы; алгоритм и seed фиксируются до результатов. 95% ДИ и число повторов — предлагаемый протокол, не исполненный тест. +3 п.п. — практический порог; ДИ и практическую значимость показываем отдельно. Не допускаем причинного вывода из наблюдательной связи и учёта выживания до поздней покупки. Для ML роль/ранг могут объяснять показатели, а случайный split строк одного аккаунта даёт утечку.'

s=new('Результаты: локальная аналитика CSV')
s.text(40,91,265,60,'87 наблюдений',26,WHITE,True)
s.text(340,91,260,60,'6 аккаунтов',26,WHITE,True)
s.text(638,91,280,60,'77 побед',26,WHITE,True)
s.text(40,151,560,34,'Число матчей по аккаунтам',17,WHITE,True)
s.chart(40,187,555,239,1)
s.placeholder(636,186,284,158,'Место для реального Superset','Сверху KPI, ниже тайминг и ΔWR\nПоказать N ранних/поздних и ДИ\nРасчёта SQL пока нет')
s.text(636,366,284,88,'В CSV 88,5% побед.\nЭто выбранные кандидаты,\nне доля побед всех игроков.',14,WHITE)
s.text(40,446,880,45,'Два аккаунта дают 60 из 87 строк (69%). Все метки smurf=1. График показывает состав данных и не подтверждает ML-гипотезы.',14,WHITE)
s.footer('Реальный расчёт task/case2/smurf_players.csv. Коды A01–A06 соответствуют аккаунтам в порядке возрастания ID')
s.notes='Источник диаграммы: night/analysis/smurf_account_summary.csv, пересчитан из task/case2/smurf_players.csv. Коды A01=307275024 (10), A02=726454100 (30), A03=818013716 (5), A04=826423518 (9), A05=945403669 (30), A06=970030081 (3). Итого 87, побед 77, 77/87*100=88.505747%. Два аккаунта с 30 строками дают 60/87=68.9655%. Все 87 матчей уникальны. Период CSV неизвестен. Медианы: GPM 711, XPM 1046, KDA 9.3333, длительность 35.3833 минуты. Значения высоки внутри выбранного файла, вывод о всей популяции и качестве классификатора невозможен. Диаграмма редактируемая, данные находятся в native chart cache. Superset в материалах не подтверждён, место подписано.'

s=new('Выводы')
items=[('01','STAGE уже созданы по подтверждению команды. Для воспроизводимой защиты нужны их версии, DQ-отчёт и run_id.'),('02','Связь тайминга Доминатора с победой ещё не проверена. Предварительная медиана 10:15 не заменяет порог очищенного среза.'),('03','CSV описывает выбранных кандидатов: 87 наблюдений по 6 аккаунтам. Винрейт 88,5% относится только к этому файлу.'),('04','Все метки положительные, peers отсутствуют. Данных недостаточно для оценки качества поиска смурфов и решений о санкциях.')]
for j,(num,body) in enumerate(items):
    yy=104+j*92; s.text(40,yy,51,52,num,24,LIME,True); s.text(109,yy,801,76,body,18,WHITE)
s.footer('Ограничения: полнота истории, незафиксированный SQL-срез и смещение отбора CSV')
s.notes='Четыре вывода опираются на подтверждение пользователя, паспорт SQL-кейса и пересчитанный CSV. Нет причинного эффекта и подтверждения/опровержения SQL-гипотезы. 10:15 — предварительное значение из прежнего профилирования, не следует употреблять его как окончательный порог. Документированные прежние объёмы RAW не объединены в новую воронку, так как относятся к разным срезам. Корректные технические ключи и арифметика CSV не обеспечивают достоверность метки smurf.'

s=new('Рекомендации и развитие')
s.table(40,104,880,[123,388,369],[
 ['Приоритет','Действие','Ожидаемый результат'],
 ['До защиты','Зафиксировать снимок SQL и период 14–15.10 UTC. Проверить ключи, DQ и первую покупку на всей паре','Достоверный состав выборки\nПроблемное событие не превращает следующую покупку в «первую»'],
 ['До защиты','Запустить MART, сохранить медиану, N, WR групп и ΔWR с кластерным ДИ. Вставить SQL/DAG/Superset фото','Проверяемый ответ по SQL-гипотезе\nКаждый результат связан с версией данных'],
 ['Следующий шаг','Собрать контроль и историю peers, определить роль/уровень и разметить top-K кандидатов','Возможность сравнить baseline и модель\nОбоснованная ручная проверка кандидатов'],
 ['Следующий шаг','Версионировать снимки и правила. Настроить контроль свежести, row count и карантин DQ','Воспроизводимость и обнаружение сбоев\nSLA проверяется измерениями']
 ],[34,74,74,74,74],12.5)
s.footer('До проверки результатов рекомендации игрокам и автоматические санкции по ML не обоснованы')
s.notes='Рекомендации прямо следуют из выявленных пробелов. Исправления SQL и проверки синтетических краевых случаев помещены в night/analysis, исходники task не менялись. Они являются кандидатом для тестового запуска, а не внедрением. Следует сверить названия реальных STAGE с проектной схемой и не публиковать витрины до DQ. Организационный вопрос: подтвердить у организаторов зачёт кастомного Доминатора как обязательного основного SQL-кейса. План ML требует источника роли, репрезентативного контроля, истории и независимой разметки.'

s=new('Командная работа')
s.text(40,87,880,37,'Роли из team.md. Ниже — предлагаемое распределение работы и передача результатов',14,WHITE)
s.table(40,143,880,[161,91,210,210,208],[
 ['Участник','Роль','Зона работы','Ключевое решение','Передача результата'],
 ['Роман Хожанец','BA','Бизнес-вопрос и критерии\nприменения результата','Порог +3 п.п. и границы\nинтерпретации ML','SA / PA: постановка\nи критерии проверки'],
 ['Сергей Голдаев','SA','Архитектура, ER\nключи и гранулярность','Одна строка покупатель–матч\nконтроль связей','DE: контракты таблиц\nи lineage'],
 ['Роман Охопков','DE','STAGE/MART, DQ\nверсии снимков и ETL','Карантин до MIN\nсогласованный snapshot','PA: витрины, run_id\nи отчёт качества'],
 ['Антон Кузьмин','PA','WR и ΔWR, ML-протокол\nвизуализация','Зависимость по матчу\nпроверка отбора CSV','Команде: выводы\nи ограничения']
 ],[34,67,67,67,67],11.8)
s.text(40,464,880,27,'Фактический вклад и владельцев кейсов команда подтверждает перед защитой',13,WHITE)
s.footer('Состав и роли подтверждены документом. Конкретные задачи в исходном team.md ещё не согласованы')
s.notes='Источник: requirements/team.md. Документ подтверждает ФИО и роли, но прямо отмечает, что индивидуальные задачи и владельцы кейсов не согласованы. Поэтому таблица — предлагаемый сценарий командной работы, не утверждение об историческом вкладе. В защите каждый участник должен понимать полную цепочку, а не только свой блок. Предлагаемый порядок выступления: BA задача/гипотезы, SA данные/архитектура, DE ETL/DQ, PA аналитика/ограничения, команда рекомендации.'

def make_chart():
    root=E.Element(q(C,'chartSpace')); sub(root,C,'lang',{'val':'ru-RU'}); sp=sub(root,C,'spPr'); fill(sp,WHITE); ln=sub(sp,A,'ln'); fill(ln,None)
    tx=sub(root,C,'txPr'); sub(tx,A,'bodyPr'); sub(tx,A,'lstStyle'); paragraph(tx,'',11,INK)
    chart=sub(root,C,'chart'); sub(chart,C,'autoTitleDeleted',{'val':'1'}); pa=sub(chart,C,'plotArea'); sub(pa,C,'layout'); bc=sub(pa,C,'barChart'); sub(bc,C,'barDir',{'val':'col'}); sub(bc,C,'grouping',{'val':'clustered'}); sub(bc,C,'varyColors',{'val':'0'}); ser=sub(bc,C,'ser'); sub(ser,C,'idx',{'val':'0'}); sub(ser,C,'order',{'val':'0'}); sub(sub(ser,C,'tx'),C,'v').text='Матчей в файле'; fill(sub(ser,C,'spPr'),PURPLE)
    catref=sub(sub(ser,C,'cat'),C,'strRef'); sub(catref,C,'f').text="'Data'!$A$2:$A$7"; cat=sub(catref,C,'strCache'); sub(cat,C,'ptCount',{'val':'6'})
    for i in range(6): sub(sub(cat,C,'pt',{'idx':str(i)}),C,'v').text=f'A{i+1:02}'
    valref=sub(sub(ser,C,'val'),C,'numRef'); sub(valref,C,'f').text="'Data'!$B$2:$B$7"; val=sub(valref,C,'numCache'); sub(val,C,'formatCode').text='0'; sub(val,C,'ptCount',{'val':'6'})
    for i,v in enumerate([10,30,5,9,30,3]): sub(sub(val,C,'pt',{'idx':str(i)}),C,'v').text=str(v)
    dl=sub(bc,C,'dLbls'); sub(dl,C,'dLblPos',{'val':'outEnd'}); sub(dl,C,'showLegendKey',{'val':'0'}); sub(dl,C,'showVal',{'val':'1'}); sub(dl,C,'showCatName',{'val':'0'}); sub(dl,C,'showSerName',{'val':'0'}); sub(bc,C,'gapWidth',{'val':'85'}); sub(bc,C,'axId',{'val':'101'}); sub(bc,C,'axId',{'val':'102'})
    for typ,ident,other,pos in [('catAx','101','102','b'),('valAx','102','101','l')]:
        ax=sub(pa,C,typ); sub(ax,C,'axId',{'val':ident}); sc=sub(ax,C,'scaling'); sub(sc,C,'orientation',{'val':'minMax'})
        if typ=='valAx': sub(sc,C,'max',{'val':'35'}); sub(sc,C,'min',{'val':'0'}); sub(ax,C,'majorGridlines')
        sub(ax,C,'delete',{'val':'0'}); sub(ax,C,'axPos',{'val':pos}); sub(ax,C,'numFmt',{'formatCode':'0','sourceLinked':'0'}); sub(ax,C,'majorTickMark',{'val':'none'}); sub(ax,C,'minorTickMark',{'val':'none'}); sub(ax,C,'tickLblPos',{'val':'nextTo'}); sub(ax,C,'crossAx',{'val':other}); sub(ax,C,'crosses',{'val':'autoZero'})
        if typ=='catAx': sub(ax,C,'lblAlgn',{'val':'ctr'}); sub(ax,C,'lblOffset',{'val':'100'})
        else: sub(ax,C,'crossBetween',{'val':'between'}); sub(ax,C,'majorUnit',{'val':'10'})
    sub(chart,C,'plotVisOnly',{'val':'1'}); sub(chart,C,'dispBlanksAs',{'val':'gap'})
    # Chart space child order follows ECMA-376. Embed literal data for Edit Data.
    root.remove(sp); root.append(sp); root.remove(tx); root.append(tx)
    ext=sub(root,C,'externalData',{q(R,'id'):'rIdWorkbook'}); sub(ext,C,'autoUpdate',{'val':'0'})
    return root

def workbook_bytes():
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    sheet=E.Element(q(ns,'worksheet')); data=sub(sheet,ns,'sheetData')
    for rownum,row in enumerate([['Account','Matches']]+[[f'A{i+1:02}',v] for i,v in enumerate([10,30,5,9,30,3])],1):
        rr=sub(data,ns,'row',{'r':str(rownum)})
        for j,value in enumerate(row):
            cc=sub(rr,ns,'c',{'r':f'{chr(65+j)}{rownum}'})
            if isinstance(value,str): cc.set('t','inlineStr'); sub(sub(cc,ns,'is'),ns,'t').text=value
            else: sub(cc,ns,'v').text=str(value)
    wb=E.Element(q(ns,'workbook')); sub(sub(wb,ns,'sheets'),ns,'sheet',{'name':'Data','sheetId':'1',q(R,'id'):'rId1'})
    content=E.Element(q(CT,'Types')); sub(content,CT,'Default',{'Extension':'rels','ContentType':'application/vnd.openxmlformats-package.relationships+xml'}); sub(content,CT,'Default',{'Extension':'xml','ContentType':'application/xml'})
    sub(content,CT,'Override',{'PartName':'/xl/workbook.xml','ContentType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'})
    sub(content,CT,'Override',{'PartName':'/xl/worksheets/sheet1.xml','ContentType':'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'})
    files={'xl/workbook.xml':xml(wb),'xl/worksheets/sheet1.xml':xml(sheet),
       '_rels/.rels':relationships([('rId1',R+'/officeDocument','xl/workbook.xml')]),
       'xl/_rels/workbook.xml.rels':relationships([('rId1',R+'/worksheet','worksheets/sheet1.xml')])}
    E.register_namespace('',CT); files['[Content_Types].xml']=xml(content)
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',zipfile.ZIP_DEFLATED) as z:
        for name,body in files.items(): z.writestr(name,body)
    return mem.getvalue()

def xml(root): return E.tostring(root,encoding='utf-8',xml_declaration=True)
def relationships(entries):
    root=E.Element(q(REL,'Relationships'))
    for ident,typ,target in entries: E.SubElement(root,q(REL,'Relationship'),{'Id':ident,'Type':typ,'Target':target})
    E.register_namespace('',REL)
    return xml(root)
def notes(text):
    root=E.Element(q(P,'notes')); cs=sub(root,P,'cSld'); tr=sub(cs,P,'spTree'); nv=sub(tr,P,'nvGrpSpPr'); sub(nv,P,'cNvPr',{'id':'1','name':''}); sub(nv,P,'cNvGrpSpPr'); sub(nv,P,'nvPr'); sub(tr,P,'grpSpPr')
    s=sub(tr,P,'sp'); nv=sub(s,P,'nvSpPr'); sub(nv,P,'cNvPr',{'id':'2','name':'Notes'}); sub(nv,P,'cNvSpPr'); sub(sub(nv,P,'nvPr'),P,'ph',{'type':'body','idx':'1'}); sub(s,P,'spPr'); tx=sub(s,P,'txBody'); sub(tx,A,'bodyPr'); sub(tx,A,'lstStyle'); paragraph(tx,text,12,INK); sub(sub(root,P,'clrMapOvr'),A,'masterClrMapping'); return root

with zipfile.ZipFile(ROOT/'requirements/Шаблон презентации.pptx') as z: parts={n:z.read(n) for n in z.namelist()}
types=E.fromstring(parts['[Content_Types].xml'])
def addtype(name,content):
    if not any(el.get('PartName')==name for el in types): E.SubElement(types,q(CT,'Override'),{'PartName':name,'ContentType':content})
for s in slides:
    parts[f'ppt/slides/slide{s.num}.xml']=xml(s.root)
    parts[f'ppt/slides/_rels/slide{s.num}.xml.rels']=relationships([('rId1',R+'/slideLayout','../slideLayouts/slideLayout1.xml'),('rIdNotes',R+'/notesSlide',f'../notesSlides/notesSlide{s.num}.xml')]+s.rels)
    parts[f'ppt/notesSlides/notesSlide{s.num}.xml']=xml(notes(s.notes))
    parts[f'ppt/notesSlides/_rels/notesSlide{s.num}.xml.rels']=relationships([('rIdSlide',R+'/slide',f'../slides/slide{s.num}.xml')])
    addtype(f'/ppt/notesSlides/notesSlide{s.num}.xml','application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml')
parts['ppt/charts/chart1.xml']=xml(make_chart()); addtype('/ppt/charts/chart1.xml','application/vnd.openxmlformats-officedocument.drawingml.chart+xml')
parts['ppt/embeddings/chart-data.xlsx']=workbook_bytes()
parts['ppt/charts/_rels/chart1.xml.rels']=relationships([('rIdWorkbook',R+'/package','../embeddings/chart-data.xlsx')])
addtype('/ppt/embeddings/chart-data.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
E.register_namespace('',CT)
parts['[Content_Types].xml']=xml(types)
# Avoid shipping a stale thumbnail from the original template.
parts.pop('docProps/thumbnail.jpeg',None)
if '_rels/.rels' in parts:
    rel=E.fromstring(parts['_rels/.rels'])
    for el in list(rel):
        if 'thumbnail' in el.get('Type',''): rel.remove(el)
    E.register_namespace('',REL)
    parts['_rels/.rels']=xml(rel)
out=NIGHT/'output/Dota2_SQL_ML.pptx'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for name,body in parts.items(): z.writestr(name,body)
(NIGHT/'build/slide_manifest.json').write_text(json.dumps([{'number':s.num,'title':s.title,'notes':s.notes} for s in slides],ensure_ascii=False,indent=2),encoding='utf-8')
(NIGHT/'output/Текст_защиты.md').write_text('# Текст и пояснения к защите\n\nРекомендуемый темп: около 8–10 минут. Подробные оговорки ниже можно использовать для ответов на вопросы.\n\n'+'\n\n'.join(f'## {s.num}. {s.title}\n\n{s.notes}' for s in slides),encoding='utf-8')
print(out)
