from pathlib import Path
from xml.sax.saxutils import escape
import re, hashlib, json
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT
from PIL import Image as PILImage
import pymupdf

ROOT=Path(r'D:\ALL\WK\Batcamp')
OUT=ROOT/'output'/'organizers'; OUT.mkdir(parents=True,exist_ok=True)
QA=ROOT/'tmp'/'etl_passport_qa'; QA.mkdir(parents=True,exist_ok=True)
for name,file in [('Arial','arial.ttf'),('ArialBold','arialbd.ttf'),('Mono','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyRU',fontName='Arial',fontSize=10.2,leading=14.3,spaceAfter=8,textColor=colors.HexColor('#19232D')))
styles.add(ParagraphStyle(name='TitleRU',fontName='ArialBold',fontSize=25,leading=30,spaceAfter=17,textColor=colors.black))
styles.add(ParagraphStyle(name='HeadRU',fontName='ArialBold',fontSize=18,leading=22,spaceAfter=13,textColor=colors.black))
styles.add(ParagraphStyle(name='SubRU',fontName='ArialBold',fontSize=11.5,leading=15,spaceBefore=9,spaceAfter=7,textColor=colors.black))
styles.add(ParagraphStyle(name='SmallRU',fontName='Arial',fontSize=8.6,leading=11.5,spaceAfter=7))
styles.add(ParagraphStyle(name='CellRU',fontName='Arial',fontSize=8.7,leading=11.8))
styles.add(ParagraphStyle(name='THRU',fontName='ArialBold',fontSize=8.7,leading=11.8,textColor=colors.white))
styles.add(ParagraphStyle(name='CodeRU',fontName='Mono',fontSize=8,leading=10.4,spaceAfter=5))
flow=[]; md=[]
def p(text,style='BodyRU'):
    flow.append(Paragraph(escape(text).replace('\n','<br/>'),styles[style])); md.append(text+'\n')
def h(text): p(text,'HeadRU'); md[-1]='## '+text+'\n'
def sub(text): p(text,'SubRU'); md[-1]='### '+text+'\n'
def page(): flow.append(PageBreak()); md.append('\n---\n')
def table(headers,rows,widths):
    data=[[Paragraph(escape(x),styles['THRU']) for x in headers]]+[[Paragraph(escape(str(x)),styles['CellRU']) for x in r] for r in rows]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#24475A')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F5F7')]),('GRID',(0,0),(-1,-1),0.45,colors.HexColor('#D9D9D9')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    flow.extend([t,Spacer(1,10)])
    md.append('| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n')
def figure(path,maxh=460):
    im=PILImage.open(path); w,h=im.size; scale=min(499/w,maxh/h)
    flow.extend([Image(str(path),w*scale,h*scale,hAlign='CENTER'),Spacer(1,9)])
    md.append('![]('+str(path.relative_to(ROOT)).replace('\\','/')+')\n')
def code(text):
    flow.append(Preformatted(text,styles['CodeRU'])); md.append('```sql\n'+text+'\n```\n')

p('Технический паспорт витрин\nДоминатор и винрейт','TitleRU')
p('ETL и Data Governance\nlakehouse.mart.dom_buyers','SubRU')
p('Команда dota_science · Буткэмп Dota 2\nВерсия 1.0 от 14 ноября 2026 года','SmallRU')
p('Документ для организаторов описывает источники, преобразования, структуру и эксплуатационные требования витрины первых покупок Helm of the Dominator. Он объединяет SQL и визуальный lineage, а также поясняет связанную командную витрину team_dominator_stats.')
p('Основной результат: подготовлена спецификация пути от PostgreSQL и MongoDB через RAW и STAGE до MART. Первая покупка определяется по паре «матч и покупатель», а ранняя группа — по общей приближённой медиане прямых сопоставлений. Скриншоты подтверждают зарегистрированные зависимости; показатели запусков отдельно требуют подтверждения.')
table(['Параметр','Значение'],[
('Основная витрина','lakehouse.mart.dom_buyers'),
('Назначение','Сравнение винрейта при ранней и поздней первой покупке предмета 164'),
('Гранулярность','Одна строка на (match_id, steam_account_id) после агрегации покупок'),
('Формат и размещение','Apache Iceberg; s3://warehouse/mart/dom_buyers — по паспорту из new'),
('Автор по исходному паспорту','Кузьмин Антон Олегович'),
('Команда домена','dota_science'),
('Ключевые потребители','Аналитика по героям, лигам и длительности; сравнение ранних и поздних покупок')],[150,349])
p('Границы документа. Это техническое приложение по кейсу 1, а не отчёт по всем кейсам проекта. Состояние описано по переданным файлам; повторного запуска кластера и проверки доступности S3 не проводилось. Ссылки [1]–[9] раскрыты в реестре источников на последней странице.','SmallRU')

page(); h('1 Архитектура и lineage основной витрины')
p('Источники матчей и участников из PostgreSQL и события покупок из MongoDB поступают в RAW. После подготовки трёх STAGE-наборов формируется dom_buyers. Скриншот Marquis / Lakehouse Portal расположен здесь как свидетельство зависимостей, до описания правил ETL. [1, 2]')
figure(ROOT/'new'/'NCh2zkXfUsvh_vqy1MGFY3bXKW5i57-vT4wqR-p3VU3hdO7pRgEwC3R_e5UZRlftlmJi1SmmaQhS9tkioh0ihjlj.jpg',425)
p('Рисунок 1. Исходный lineage dom_buyers из папки new. Подписи узлов в интерфейсе сокращены; полные имена входов зафиксированы в таблице ниже. Изображение сохранено без изменения содержания. [2]','SmallRU')
table(['RAW','STAGE по SQL MART'],[
('lakehouse.raw.pg__matches','lakehouse.stage.matches_fixed'),
('lakehouse.raw.pg__match_players','lakehouse.stage.match_players'),
('lakehouse.raw.mongo__purchase_events','lakehouse.stage.purchase_events_new')],[249,250])
p('Все три STAGE-входа используются основной MART-витриной. До Superset граф на рисунке не доведён: BI является аналитическим потребителем по назначению, но его зависимости этим скриншотом не подтверждаются. [1, 2]','SmallRU')

page(); h('2 Логика ETL и аналитический контракт')
sub('Подготовка STAGE')
p('Матчи: выбирается последняя версия по loaded_at; точные повторы схлопываются. Если у последней версии одного match_id остаются разные записи, ключ исключается. Режимы 15, 18, 19, 20, 21, 23 и лобби 1, 4, 8 исключаются. Значения NULL режима и лобби сохраняются. Проверки положительной длительности в сохранённом SQL нет. [5]')
p('Участники: ROW_NUMBER оставляет одну запись на (match_id, player_slot) с приоритетом src_modified_stamp и дополнительных полей. Покупки: поля приводятся к типам, точные повторы удаляются; конфликтующие версии одного id исключаются. В обоих запросах есть соединение со stage.matches. Это имя отличается от stage.matches_fixed в MART; соответствие объектов требуется сверить с фактическим DAG. [5]')
sub('Преобразование dom_buyers')
table(['Шаг','Фактическое правило SQL'],[
('1 buys','itemid = 164 и time >= 0; MIN(time) по (match_id, steam_account_id)'),
('2 players','account_id IS NOT NULL и account_id <> 4294967295; одна строка на (match_id, account_id) по минимальному player_slot'),
('3 j','INNER JOIN с matches_fixed по match_id; LEFT JOIN с players по матчу и аккаунту'),
('4 med','approx_percentile(buy_time, 0.5) по строкам is_direct'),
('5 результат','resolution = direct при найденном участнике, иначе hidden; медиана добавляется ко всем строкам через CROSS JOIN')],[88,411])
sub('Метрики и правила использования')
p('Для direct признак is_early равен buy_time <= median_buy_sec. Для hidden поля win и is_early равны NULL; такие строки не включаются в сравнение винрейтов. Основная метрика — 100 × (винрейт ранней группы − винрейт поздней группы), в процентных пунктах. Знаменатель — покупатели в матчах, а не уникальные матчи. Цель паспорта кейса: не менее +3 п.п. [1, 4, 6]')
p('Медиана общая для прямых сопоставлений витрины; при фильтрации графиков её не следует заменять медианой каждой подгруппы. Равные порогу времена относятся к ранней группе. Период кейса заявлен как 14–15 октября 2026 UTC; текущий SQL MART не фильтрует start_time и сам этот период не подтверждает. [4, 6]')

page(); h('3 Словарь данных основной витрины')
p('Типы ниже воспроизводят декларацию из new/task.txt. Это описание схемы: сочетание varchar и STRING требует согласования диалекта перед выполнением DDL. Полный SELECT приведён в приложении. [1]','SmallRU')
table(['Поле','Тип в паспорте','Смысл и правило'],[
('match_id','bigint','Матч; часть логического ключа'),('steam_account_id','bigint','Покупатель; часть логического ключа'),
('buy_time','integer','Первая неотрицательная покупка, секунды от начала'),('resolution','varchar','direct / hidden по наличию участника'),
('player_slot','integer','Слот участника, для hidden — NULL'),('hero_id','integer','Идентификатор героя сопоставленного участника'),
('rank_raw','integer','Исходный rank без перекодировки'),('league','integer','0 при rank NULL/0; иначе floor((rank_raw−1)/10)+1'),
('is_radiant','boolean','Сторона сопоставленного участника'),('win','integer','1 при p.win = true, иначе 0 для direct; NULL для hidden'),
('duration','integer','Длительность матча в секундах'),('game_mode','integer','Режим из matches_fixed'),('lobby_type','integer','Тип лобби из matches_fixed'),
('dur_bucket','varchar','<30; 30–40; 40–50; 50+ минут'),('buy_bucket','varchar','<6; 6–8; 8–10; 10–12; 12–15; 15–20; 20+ минут'),
('median_buy_sec','integer','Общая приближённая медиана; SELECT не приводит тип явно'),('is_early','boolean','Для direct: buy_time <= median; для hidden NULL'),
('job_id','STRING','UUID запуска; объявлен в DDL, отсутствует в SELECT'),('sys_insert_stamp','TIMESTAMP','Время записи; объявлено, отсутствует в SELECT'),('src_modified_stamp','TIMESTAMP','Метка источника; объявлена, отсутствует в SELECT')],[120,85,294])
p('Логический ключ не объявлен физическим PRIMARY KEY в исходном DDL. Уникальность зависит от агрегации buys и уникальности матчей в STAGE. Для аккаунта NULL формируется отдельная группа покупок в матче, которую нельзя трактовать как одного установленного игрока. [1, 4]','SmallRU')

page(); h('4 Data Governance и качество данных')
sub('Правила, подтверждённые сохранённым кодом')
p('Покупки предмета 164 с отрицательным или NULL time не участвуют в расчёте. При повторных покупках используется минимум оставшихся времён. Несопоставленные покупки сохраняются для контроля покрытия. Значение resolution = hidden означает отсутствие прямого соответствия в SQL и не доказывает причину анонимности аккаунта. [4]')
sub('Уточнения к исходному описанию')
table(['Область','Состояние и влияние'],[
('Аккаунты','Описание new заявляет исключение NULL, 0 и 4294967295. SQL фильтрует только NULL и 4294967295 в players. В buys эти фильтры отсутствуют; account_id = 0 может получить direct.'),
('Однозначность','ROW_NUMBER выбирает минимальный слот аккаунта. Если аккаунт встречается в нескольких слотах, выбор строки не подтверждает однозначную связь.'),
('Предел времени','Проверки buy_time <= duration нет. При отрицательном событии и положительном событии пары сохраняется положительное; паспорт кейса требует исключать всю пару.'),
('Число событий','Правило исключения пары с более чем двумя событиями Доминатора из паспорта кейса в SQL MART не реализовано.'),
('Исход и NULL','Для direct значение p.win = NULL попадает в ELSE 0. При NULL duration получается последний dur_bucket, поэтому нужна отдельная проверка пропусков.'),
('Ранг','Формула league подтверждена кодом. Соответствие диапазонов rank_raw названиям рангов из исходного текста отдельно не проверено.'),
('Аудит и перезапуск','job_id и временные метки заявлены в DDL. Их заполнение, режим записи, инкременты и идемпотентность не подтверждаются одним SELECT.')],[99,400])
sub('Контроль качества при следующей загрузке')
p('Рекомендуемые проверки: уникальность ключа результата; число NULL и нулевых аккаунтов; доля hidden; число строк с win IS NULL среди direct; время за пределами матча; конфликты аккаунтов по слотам; число исключённых пар и покрытие периода. Пороговые значения и поведение DAG при нарушении пока не согласованы. Это требования к контролю, а не отчёт о пройденных проверках. [4–6]')

page(); h('5 Оркестрация и эксплуатационный паспорт')
p('В new/task.txt заявлен DAG mart__dom_buyers с файлом /opt/airflow/dags/generated/mart__dom_buyers.py. Запуск описан как событийный: AND-условие на три Airflow Dataset — lakehouse://stage/match_players, lakehouse://stage/matches_fixed и lakehouse://stage/purchase_events_new. Состав заявлен как 3 PythonOperator и 1 SparkSubmitOperator. Экспорт DAG и журналы запусков в new отсутствуют. [1]')
table(['Параметр','Зафиксированное состояние'],[
('Обновление','По new: после обновления всех трёх STAGE-входов. Требование кейса: раз в час при изменении входных данных; для неизменного среза первоначальная сборка.'),
('Глубина данных','По паспорту кейса: весь доступный срез матчей 14–15 октября 2026 UTC и связанные события. Фактическое покрытие не выгружено.'),
('Хранение','Требование кейса: до конца буткэмпа и ещё 30 календарных дней после защиты. Настройки удаления и хранения не представлены.'),
('SLA и актуальность','Дедлайн доступности, допустимое отставание, часовой пояс SLA и пороги оповещения не зафиксированы. Событийный триггер сам по себе SLA не определяет.'),
('Наблюдаемые запуски','В исходном описании указаны 100% успешности и среднее ≈ 2 мин 8 с. Период, число запусков и логи отсутствуют; показатели приведены как заявленные.'),
('Объём и рост','Число строк текущей MART, размер Iceberg и прирост за загрузку не приложены; нужны метрики фактического снимка.'),
('Повторный запуск','Режим append / overwrite / MERGE, watermark, retries и backfill не установлены по переданным материалам.'),
('Доступ к данным','Есть идентификаторы аккаунтов. Классификация данных, роли доступа, маскирование и ответственный за разрешения отдельно не определены.')],[108,391])
sub('Условие воспроизводимой публикации')
p('Для подтверждения эксплуатации следует связать версию SQL, DAG run_id и Iceberg snapshot_id, сохранить число входных и выходных строк, протокол DQ и времена завершения STAGE/MART. Согласовать часовой SLA и политику повторной записи. Эти сведения позволят отделить зарегистрированные зависимости от факта успешного обновления. [7, 8]')

page(); h('6 Lineage командной витрины')
p('Дополнительная витрина lakehouse.mart.team_dominator_stats использует те же три STAGE-входа. Она рассчитывается непосредственно из них, без чтения dom_buyers. Единица анализа — сторона в матче. [3, 4]')
figure(ROOT/'new'/'D1MzDbpRXUwD2qn2BxMN6D1PACOvXjnbCS3RGW_CEEVD6V7-y0IvKme77KZKo5VSRwTC1k9qSemeh6x9C4a7ADVM.jpg',460)
p('Рисунок 2. Исходный lineage team_dominator_stats из папки new. Он подтверждает отдельную ветвь от RAW/STAGE к командной MART. [3]','SmallRU')
sub('Отбор команд и матчей')
p('SQL требует две стороны, по пять различных player_slot на каждой и сумму командных win = 1. Вся пара команд исключается, если у любого участника account_id IS NULL или account_id = 4294967295. Отбор отличается от основного набора покупателей, поэтому метрики витрин описывают разные выборки. [4]')

page(); h('7 Контракт командной витрины')
table(['Поле или группа','Содержание'],[
('match_id, is_radiant','Логический ключ: матч и сторона'),('win','Максимум индивидуальных флагов победы команды'),
('duration, game_mode, lobby_type','Атрибуты матча из matches_fixed'),('dur_bucket','Те же интервалы длительности, что в dom_buyers'),
('players_in_slots','Количество различных слотов стороны; допускается 5'),('hidden_players','Число строк с NULL / 4294967295 account_id'),
('dom_cnt','COUNT(dp.buy_time) после соединения участников и событий предмета 164'),('team_has_dom','dom_cnt > 0'),
('first_dom_time','MIN времени события покупки в команде'),('match_has_hidden_buyer','Константа false в финальном SELECT')],[160,339])
sub('Ограничения интерпретации')
p('dom_cnt считает события с заполненным buy_time, включая 0, а не уникальных покупателей. Повторные покупки одного игрока увеличивают показатель. В командном SQL нет фильтра time >= 0 или проверки времени относительно duration, поэтому first_dom_time может отличаться от минимального времени основной витрины. [4]')
p('match_has_hidden_buyer всегда равен false в коде. Поле не является самостоятельной проверкой всех несопоставленных событий покупок: исключение bad_matches основано на участниках, а не на полном покрытии purchase_events_new. Аналогично, MAX(win) и проверка суммы командных побед не устанавливают согласованность каждого участника с radiant_win. [4]')
sub('Назначение двух витрин')
p('dom_buyers отвечает на вопрос о времени первой покупки у покупателя и его исходе. team_dominator_stats позволяет сравнивать наличие предмета у стороны и длительность матча. Сравнение «есть предмет / нет предмета» не заменяет сравнение ранней и поздней покупки. Наблюдаемые зависимости не устанавливают причинное влияние предмета на победу. [4, 6]')
sub('Проверка для организаторов')
p('Полный SQL командной витрины доступен в task/case1/mart/team_dominator_stats.sql. В данном документе он представлен контрактом полей и отдельным исходным lineage, чтобы не смешивать его с основным SQL dom_buyers. [4]')

page(); h('Приложение А Декларация схемы')
p('Ниже приведён DDL из исходного паспорта без комментариев полей; их смысл раскрыт в словаре данных. DDL сохраняет типы источника и не заявляется как проверенный скрипт развёртывания. Для исполнения нужно выбрать диалект и определить параметры Iceberg и location. [1]')
code('''CREATE TABLE lakehouse.mart.dom_buyers (
  match_id bigint,
  steam_account_id bigint,
  buy_time integer,
  resolution varchar,
  player_slot integer,
  hero_id integer,
  rank_raw integer,
  league integer,
  is_radiant boolean,
  win integer,
  duration integer,
  game_mode integer,
  lobby_type integer,
  dur_bucket varchar,
  buy_bucket varchar,
  median_buy_sec integer,
  is_early boolean,
  job_id STRING,
  sys_insert_stamp TIMESTAMP,
  src_modified_stamp TIMESTAMP
);''')
sub('Сопоставление DDL и SELECT')
p('DDL содержит 20 полей, SELECT возвращает 17 бизнес-полей. job_id, sys_insert_stamp и src_modified_stamp должен заполнять внешний механизм записи либо дополнительная проекция. Такого механизма в переданном SQL нет. Наличие аудиторских колонок в декларации само по себе не подтверждает инкрементальную или идемпотентную загрузку.')
p('approx_percentile не приведён явно к integer, хотя median_buy_sec объявлен integer. Перед публикацией следует сверить тип результата с движком и фактической Iceberg-схемой. Первичный ключ, партиционирование и политика эволюции схемы в исходном DDL не заданы.')

txt=(ROOT/'new'/'task.txt').read_text(encoding='utf-8-sig')
sql=txt.split('5. Transformation SQL Pipeline',1)[1].strip()
lines=sql.splitlines(); split=next(i for i,l in enumerate(lines) if l.startswith('SELECT j.match_id'))
page(); h('Приложение Б SQL основной витрины')
p('Часть 1 из 2. Исходный SQL из раздела 5 new/task.txt. Случайный повтор фрагмента запроса перед разделом 5 исключён; логика полного запроса сохранена. Это SELECT-преобразование без команды записи и без заполнения системных полей. [1, 4]','SmallRU')
code('\n'.join(lines[:split]))
page(); h('Приложение Б SQL основной витрины')
p('Часть 2 из 2. Продолжение того же запроса. [1]','SmallRU')
code('\n'.join(lines[split:]))

page(); h('Реестр источников и статус сведений')
p('Все ссылки относятся к переданному проекту. Внешние источники не использовались. Исходные файлы new и task сохранены без изменения. Дата фиксации документа: 14 ноября 2026 года.')
table(['№','Источник в проекте','Использование'],[
('[1]','new/task.txt','Паспорт dom_buyers, DDL, SQL, заявленные свойства Airflow'),
('[2]','new/NCh2…h0ihjlj.jpg','Рисунок 1: lineage dom_buyers'),
('[3]','new/D1Mz…4a7ADVM.jpg','Рисунок 2: lineage team_dominator_stats'),
('[4]','task/case1/mart/dom_buyers.sql; team_dominator_stats.sql','Сверка преобразований и командный контракт'),
('[5]','task/case1/stages/matches_fixed.sql; match_players.sql; purchase_events.sql','Правила STAGE и расхождения имён входов'),
('[6]','task/case1/case_definition.md; hypothesis_analysis.md','Цель, метрика, эксплуатационные требования и ограничения'),
('[7]','requirements/Постановка_проекта_буткемп.txt','Состав эксплуатационного паспорта'),
('[8]','requirements/Критерии оценки проекта.md','Требования к ETL, DG, lineage и SLA'),
('[9]','task/case1/mart/README.md','Альтернативное описание витрин; фактическим контрактом здесь принят SQL из new')],[27,257,215])
sub('Как читать статус утверждений')
p('Подтверждено кодом: правила SELECT, состав полей, условия соединений, агрегации и фильтры. Подтверждено изображениями: зарегистрированные зависимости до MART. Заявлено в описании: S3-путь, формат, автор, конфигурация DAG и показатели запусков. Определено как требование: период, часовой пересчёт и срок хранения из паспорта кейса.')
p('Для подтверждения рабочей конфигурации остаются нужны экспорт DAG и определений таблиц, журнал запусков, снимок Iceberg и результаты DQ. Указанные пробелы ограничивают проверку эксплуатации; они не изменяют содержание приложенного исходного SQL.')
sub('Состав передаваемого артефакта')
p('Этот PDF содержит паспорт, два оригинальных lineage, словарь данных, правила качества, эксплуатационные требования, контракт командной витрины и полный SQL dom_buyers. Редактируемый текстовый исходник хранится рядом с PDF. Отдельный технический манифест фиксирует полные имена и SHA-256 использованных файлов.')

def footer(c,doc):
    c.setStrokeColor(colors.HexColor('#CBD5DB')); c.setLineWidth(.4); c.line(48,43,547,43)
    c.setFont('Arial',8); c.setFillColor(colors.HexColor('#51616B'))
    c.drawString(48,29,'dota_science  /  ETL и Data Governance  /  14.11.2026')
    c.drawRightString(547,29,str(doc.page))
pdf=OUT/'Dota2_ETL_DG_Passport.pdf'
doc=SimpleDocTemplate(str(pdf),pagesize=(595.28,841.89),rightMargin=48,leftMargin=48,topMargin=43,bottomMargin=58,title='Технический паспорт витрин Доминатор и винрейт',author='dota_science')
doc.build(flow,onFirstPage=footer,onLaterPages=footer)
(OUT/'Dota2_ETL_DG_Passport.md').write_text('\n'.join(md),encoding='utf-8')
sources=[ROOT/'new'/'task.txt',*sorted((ROOT/'new').glob('*.jpg')),*sorted((ROOT/'task'/'case1'/'mart').glob('*.sql')),*sorted((ROOT/'task'/'case1'/'stages').glob('*.sql')),ROOT/'task/case1/case_definition.md',ROOT/'task/case1/hypothesis_analysis.md',ROOT/'requirements/Постановка_проекта_буткемп.txt',ROOT/'requirements/Критерии оценки проекта.md']
sources.append(ROOT/'task/case1/mart/README.md')
manifest=[{'path':str(f.relative_to(ROOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sources]
(QA/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
from zipfile import ZipFile, ZIP_DEFLATED
with ZipFile(OUT/'Dota2_ETL_DG_Submission.zip','w',ZIP_DEFLATED) as z:
    z.write(pdf,pdf.name)
    z.write(OUT/'Dota2_ETL_DG_Passport.md','Dota2_ETL_DG_Passport.md')
    z.write(QA/'sources.json','sources.json')
    for src in sources: z.write(src,str(src.relative_to(ROOT)).replace('\\','/'))
    z.writestr('README.txt','Основной документ для организаторов: Dota2_ETL_DG_Passport.pdf\nРедактируемый текст: Dota2_ETL_DG_Passport.md\nВ new, task и requirements сохранены использованные первоисточники.\nsources.json содержит их полные пути и SHA-256.\n')
d=pymupdf.open(pdf)
for i,pg in enumerate(d): pg.get_pixmap(matrix=pymupdf.Matrix(1.25,1.25)).save(QA/f'page-{i+1:02}.png')
print(json.dumps({'pages':len(d),'pdf':str(pdf),'page_text_lengths':[len(pg.get_text()) for pg in d]},ensure_ascii=False))
