/* Minimal offline OOXML XLSX writer. No external CDN, libraries or requests.
   Spreadsheet styles are impossible in CSV, so use this for colored results. */
(function(root,factory){
 const api=factory();if(typeof module==="object"&&module.exports)module.exports=api;
 root.VoidscanXlsx=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
"use strict";
const enc=new TextEncoder();
function escapeXml(v){return String(v??"").replace(/&/g,"&amp;").replace(/</g,"&lt;")
 .replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&apos;")
 .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g,"");}
function colIndex(n){let s="";for(let i=n+1;i>0;i=Math.floor((i-1)/26))s=String.fromCharCode(65+(i-1)%26)+s;return s;}
function cell(addr,value,style){
 const v=value===null||value===undefined?"":String(value);
 return '<c r="'+addr+'" s="'+style+'" t="inlineStr"><is><t xml:space="preserve">'+escapeXml(v)+'</t></is></c>';
}
function widths(rows,cols){
 return cols.map(c=>{
  let chars=c.label.length;
  for(const r of rows.slice(0,1200)){
    const v=String(r[c.key]??"");
    const visible=v.split(/[\r\n|]/)[0]; // long content wraps in Excel.
    chars=Math.max(chars,Math.min(visible.length,75));
  }
  const cap=/evidence|photoIds/i.test(c.key)?68:/profileUrl/i.test(c.key)?58:42;
  return Math.min(cap,Math.max(12,chars+3));
 });
}
const PK=0x04034b50,CD=0x02014b50,END=0x06054b50;
const CRC_TABLE=(()=>{
 const t=new Uint32Array(256);
 for(let n=0;n<256;n++){let c=n;for(let i=0;i<8;i++)c=(c&1)?0xedb88320^(c>>>1):c>>>1;t[n]=c>>>0;}
 return t;
})();
function crc32(data){let c=0xffffffff;for(let i=0;i<data.length;i++)c=CRC_TABLE[(c^data[i])&255]^(c>>>8);return (c^0xffffffff)>>>0;}
function zip(entries){
 const chunks=[],central=[];let position=0;
 function push(u){chunks.push(u);position+=u.length;}
 function writeHeader(size,writer){const buffer=new ArrayBuffer(size),view=new DataView(buffer);writer(view);return new Uint8Array(buffer);}
 for(const [name,text] of entries){
   const n=enc.encode(name),data=enc.encode(text),crc=crc32(data),start=position;
   push(writeHeader(30,v=>{v.setUint32(0,PK,true);v.setUint16(4,20,true);v.setUint16(6,0,true);
     v.setUint16(8,0,true);v.setUint32(14,crc,true);v.setUint32(18,data.length,true);
     v.setUint32(22,data.length,true);v.setUint16(26,n.length,true);}));
   push(n);push(data);
   const c=writeHeader(46,v=>{v.setUint32(0,CD,true);v.setUint16(4,20,true);
     v.setUint16(6,20,true);v.setUint32(16,crc,true);v.setUint32(20,data.length,true);
     v.setUint32(24,data.length,true);v.setUint16(28,n.length,true);v.setUint32(42,start,true);});
   central.push(c,n);
 }
 const centralAt=position;
 for(const chunk of central)push(chunk);
 const centralSize=position-centralAt;
 push(writeHeader(22,v=>{v.setUint32(0,END,true);v.setUint16(8,entries.length,true);
   v.setUint16(10,entries.length,true);v.setUint32(12,centralSize,true);
   v.setUint32(16,centralAt,true);}));
 const output=new Uint8Array(position);let at=0;
 for(const chunk of chunks){output.set(chunk,at);at+=chunk.length;}
 return output;
}
function makeRows(rows,cols){
 const header='<row r="1" ht="32" customHeight="1">'+
   cols.map((c,i)=>cell(colIndex(i)+"1",c.label,1)).join("")+'</row>';
 const columnWidths=widths(rows,cols);
 const body=rows.map((r,idx)=>{
  const row=idx+2;
  const lines=Math.max(1,...cols.map((c,i)=>{
   const content=String(r[c.key]??"");
   const safeWidth=Math.max(8,columnWidths[i]-3);
   return content.split(/\r?\n/).reduce((count,part)=>count+Math.max(1,Math.ceil(part.length/safeWidth)),0);
  }));
  const height=Math.min(280,Math.max(29,Math.ceil(lines*16+9)));
  return '<row r="'+row+'" ht="'+height+'" customHeight="1">'+cols.map((c,i)=>{
   const value=r[c.key]??"",isStatus=c.key==="status";
   const style=isStatus?(value==="nghi vấn"?2:3):0;
   return cell(colIndex(i)+row,value,style);
  }).join("")+'</row>';
 }).join("");
 return header+body;
}
function sheetXml(rows,cols){
 const end=colIndex(cols.length-1)+(rows.length+1);
 const ws=widths(rows,cols);
 const colsXml='<cols>'+ws.map((w,i)=>'<col min="'+(i+1)+'" max="'+(i+1)+
   '" width="'+w+'" customWidth="1"/>').join("")+'</cols>';
 const n=rows.length+1;
 return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
  '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '+
  'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'+
  '<dimension ref="A1:'+end+'"/>'+
  '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'+
  '<sheetFormatPr defaultRowHeight="20"/>'+colsXml+
  '<sheetData>'+makeRows(rows,cols)+'</sheetData>'+
  '<autoFilter ref="A1:'+end+'"/>'+
  '<hyperlinks>'+rows.map((row,i)=>{
    const u=String(row.profileUrl||"");
    if(!/^https:\/\/(?:www\.|m\.|web\.)?facebook\.com\//.test(u))return "";
    return '<hyperlink ref="A'+(i+2)+'" r:id="hl'+(i+1)+'"/>';
  }).join("")+'</hyperlinks>'+
  '<pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>'+
  '</worksheet>';
}
const STYLES='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
'<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'+
'<fonts count="3"><font><sz val="10"/><name val="Aptos"/><color rgb="FF141A27"/></font>'+
'<font><b/><sz val="11"/><name val="Aptos"/><color rgb="FFFFFFFF"/></font>'+
'<font><b/><sz val="10"/><name val="Aptos"/><color rgb="FF252525"/></font></fonts>'+
'<fills count="5"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'+
'<fill><patternFill patternType="solid"><fgColor rgb="FF2158AD"/><bgColor indexed="64"/></patternFill></fill>'+
'<fill><patternFill patternType="solid"><fgColor rgb="FFFDE8E8"/><bgColor indexed="64"/></patternFill></fill>'+
'<fill><patternFill patternType="solid"><fgColor rgb="FFE4F5E8"/><bgColor indexed="64"/></patternFill></fill></fills>'+
'<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>'+
'<border><left style="thin"><color rgb="FFDAE2ED"/></left>'+
'<right style="thin"><color rgb="FFDAE2ED"/></right>'+
'<top style="thin"><color rgb="FFDAE2ED"/></top>'+
'<bottom style="thin"><color rgb="FFDAE2ED"/></bottom><diagonal/></border></borders>'+
'<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'+
'<cellXfs count="4">'+
'<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'+
'<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'+
'<xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'+
'<xf numFmtId="0" fontId="2" fillId="4" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'+
'</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>';
function workbook(rows,columns){
 if(!Array.isArray(rows)||!Array.isArray(columns)||!columns.length)throw Error("Bảng Excel không hợp lệ.");
 if(rows.length>100000)throw Error("Tệp quá lớn (trên 100.000 dòng).");
 const sheet=sheetXml(rows,columns);
 const hyperlinkRels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+
  rows.map((row,i)=>{
   const url=String(row.profileUrl||"");
   if(!/^https:\/\/(?:www\.|m\.|web\.)?facebook\.com\//.test(url))return "";
   return '<Relationship Id="hl'+(i+1)+'" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="'+escapeXml(url)+'" TargetMode="External"/>';
  }).join("")+'</Relationships>';
 const main='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
  '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '+
  'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'+
  '<sheets><sheet name="Ket qua kiem toan" sheetId="1" r:id="rId1"/></sheets></workbook>';
 const workbookRels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+
  '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'+
  '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>';
 const rels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+
  '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>';
 const types='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
  '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'+
  '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'+
  '<Default Extension="xml" ContentType="application/xml"/>'+
  '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'+
  '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'+
  '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'+
  '</Types>';
 return zip([
  ["[Content_Types].xml",types],["_rels/.rels",rels],
  ["xl/workbook.xml",main],["xl/_rels/workbook.xml.rels",workbookRels],
  ["xl/styles.xml",STYLES],["xl/worksheets/sheet1.xml",sheet],
  ["xl/worksheets/_rels/sheet1.xml.rels",hyperlinkRels]
 ]);
}
return {workbook,widths,zip};
});