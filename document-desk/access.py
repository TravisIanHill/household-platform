"""Document permissions. Deny by default; explicit private beats inherited rules."""
def can_view(doc,user,people,policies):
    return permission(doc,user,people,policies) in ('view','edit')

def permission(doc,user,people,policies):
    if not user:return None
    if user['role']=='admin' or doc.get('owner_id')==user['id']:return 'edit'
    mode=doc.get('visibility','household')
    if mode=='private':return None
    if mode=='household':return 'view'
    linked={p['id'] for p in people if p.get('user_id')==user['id']}
    is_person=bool(linked & set(doc.get('person_ids',[])))
    if mode=='personal_adults':return 'view' if user.get('adult') or is_person else None
    if mode=='selected':return 'view' if user['id'] in doc.get('shared_user_ids',[]) else None
    if mode!='inherit':return None
    folder=doc.get('folder','');best=None
    for rule in policies:
        target=rule['target']
        match=(rule['kind']=='folder' and (folder==target or folder.startswith(target+'/'))) or (rule['kind']=='collection' and target in doc.get('collections',[]))
        granted=(rule.get('adults') and user.get('adult')) or (rule.get('person_owners') and is_person) or user['id'] in rule.get('user_ids',[])
        if match and granted:
            best='edit' if rule.get('permission')=='edit' else best or 'view'
    return best
