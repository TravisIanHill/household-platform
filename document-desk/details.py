"""Typed details and conservative OCR suggestions; never writes inferred values."""
import re
from datetime import datetime
STATES='Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|District of Columbia|American Samoa|Guam|Northern Mariana Islands|Puerto Rico|U.S. Virgin Islands'.split('|')
BIRTH_FIELDS=['Person','Date of birth','City of birth','County of birth','Country','State or territory','Issuing agency—as printed','Date issued','Notes']
COUNTRIES=['United States','Canada','Mexico','United Kingdom','Other']
BIRTH_SCHEMA={'Person':{'type':'person'},'Date of birth':{'type':'date'},'Date issued':{'type':'date'},'Country':{'type':'select','options':COUNTRIES},'State or territory':{'type':'select','options':STATES}}

def suggest(text,people):
    suggestions={};person_ids=[]
    def add(field,value,evidence):
        if value:suggestions[field]={'value':value,'evidence':evidence[:300]}
    if not re.search(r'BIRTH\s+CERTIFICATE',text,re.I):return dict(type=None,fields={},person_ids=[],message='No supported birth-certificate pattern found. Review manually.')
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    normalized=' '.join(re.findall(r'\w+',text)).casefold()
    for p in people:
        names=[p['name']]+p.get('aliases',[])
        for name in names:
            needle=' '.join(re.findall(r'\w+',name)).casefold()
            if len(needle)>3 and re.search(r'\b'+re.escape(needle)+r'\b',normalized):
                # Match only near FULL NAME or CHILD to avoid matching a parent.
                match=re.search(r'(?:FULL\s+NAME|CHILD[’\x27]?S?\s+NAME)\s*[:\n ]+([^\n]+)',text,re.I)
                if match and needle in ' '.join(re.findall(r'\w+',match[1])).casefold():
                    person_ids.append(p['id']);add('Person',match[1].strip(),match[0]);break
    # US jurisdiction is suggested only when explicitly stated.
    for state in sorted(STATES,key=len,reverse=True):
        match=re.search(r'\bSTATE\s+OF\s+'+re.escape(state)+r'\b',text,re.I)
        if match:add('State or territory',state,match[0]);add('Country','United States',match[0]);break
    date_pattern=r'\b(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{1,2},?\s+\d{4}\b'
    for label,field in [('DATE OF BIRTH','Date of birth'),('DATE ISSUED','Date issued'),('DATE OF ISSUE','Date issued')]:
        match=re.search(label+r'[\s\S]{0,100}?('+date_pattern+r')',text,re.I)
        if match:
            try:value=datetime.strptime(re.sub(r',','',match[1]).title(),'%B %d %Y').date().isoformat();add(field,value,match[0])
            except ValueError:pass
    # Only exact label/value lines; do not invent city/county or issuing agency.
    for label,field in [('CITY OF BIRTH','City of birth'),('COUNTY OF BIRTH','County of birth'),('ISSUING AGENCY','Issuing agency—as printed')]:
        match=re.search(r'(?im)^'+label+r'\s*:\s*([^\n]+)',text)
        if match:add(field,match[1].strip(),match[0])
    return dict(type='Birth Certificate',fields=suggestions,person_ids=list(set(person_ids)),message='Suggestions only. Confirm against the original; existing values are never overwritten automatically.')
