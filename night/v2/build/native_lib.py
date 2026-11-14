"""Native OOXML authoring fallback: the supplied @oai/artifact-tool runtime is absent.
Uses the supplied template package, preserves its 11-slide sequence and canvas.
No python-pptx or external dependencies. All output paths are below night.
"""
from pathlib import Path
import xml.etree.ElementTree as E
import zipfile, json, copy, html, io

ROOT=Path(__file__).resolve().parents[3]
NIGHT=ROOT/'night/v2'
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

