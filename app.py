import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text

app=Flask(__name__)
app.secret_key=os.environ.get('SECRET_KEY','change-this-secret-key')
ADMIN_PASSWORD=os.environ.get('ADMIN_PASSWORD','1234')
DATABASE_URL=os.environ.get('DATABASE_URL','sqlite:///championship.db')
if DATABASE_URL.startswith('postgres://'): DATABASE_URL=DATABASE_URL.replace('postgres://','postgresql+psycopg://',1)
elif DATABASE_URL.startswith('postgresql://'): DATABASE_URL=DATABASE_URL.replace('postgresql://','postgresql+psycopg://',1)
engine=create_engine(DATABASE_URL, pool_pre_ping=True)
PHASES=['Inscrições','Fase de Grupos','Oitavas de Final','Quartas de Final','Semifinal','Final']
GROUPS=list('ABCDEFGH')

def init_db():
    with engine.begin() as c:
        c.execute(text('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, phase VARCHAR(80) NOT NULL, name VARCHAR(120) NOT NULL)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY, name VARCHAR(120) NOT NULL, nickname VARCHAR(120), group_name VARCHAR(1) NOT NULL DEFAULT \'A\', status VARCHAR(20) NOT NULL DEFAULT \'pending\')'))
        c.execute(text('CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY, phase VARCHAR(80) NOT NULL, group_name VARCHAR(1), player1_id INTEGER, player2_id INTEGER, score1 INTEGER, score2 INTEGER, played INTEGER DEFAULT 1)'))
        if not c.execute(text('SELECT id FROM settings WHERE id=1')).first(): c.execute(text("INSERT INTO settings(id,phase,name) VALUES(1,'Fase de Grupos','FC Championship')"))
        # SQLite needs autoincrement handled by app ids; postgres integer PK won't auto increment, so use max+1 helper.

def next_id(c, table):
    row=c.execute(text(f'SELECT COALESCE(MAX(id),0)+1 AS n FROM {table}')).first(); return row.n

def rows(q, **kw):
    with engine.begin() as c: return c.execute(text(q),kw).mappings().all()
def one(q, **kw):
    with engine.begin() as c: return c.execute(text(q),kw).mappings().first()

def admin_required(f):
    @wraps(f)
    def wrap(*a,**kw):
        if not session.get('admin'): return redirect(url_for('login'))
        return f(*a,**kw)
    return wrap

def standings(players,matches):
    s={p['id']:{'name':p['name'],'nickname':p['nickname'],'group':p['group_name'],'j':0,'v':0,'e':0,'d':0,'gp':0,'gc':0,'sg':0,'pts':0} for p in players}
    for m in matches:
        if m['phase']!='Fase de Grupos' or not m['played'] or m['player1_id'] not in s or m['player2_id'] not in s: continue
        a,b=s[m['player1_id']],s[m['player2_id']]; x,y=m['score1'],m['score2']; a['j']+=1;b['j']+=1;a['gp']+=x;a['gc']+=y;b['gp']+=y;b['gc']+=x
        if x>y:a['v']+=1;b['d']+=1;a['pts']+=3
        elif x<y:b['v']+=1;a['d']+=1;b['pts']+=3
        else:a['e']+=1;b['e']+=1;a['pts']+=1;b['pts']+=1
    for x in s.values(): x['sg']=x['gp']-x['gc']
    return {g:sorted([x for x in s.values() if x['group']==g],key=lambda z:(-z['pts'],-z['sg'],-z['gp'],z['name'].lower())) for g in GROUPS}

@app.route('/login',methods=['GET','POST'])
def login():
    init_db()
    settings = one('SELECT * FROM settings WHERE id=1')

    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))

        flash('Senha incorreta.')

    return render_template('login.html', settings=settings)

def logout(): session.clear(); return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin():
    init_db(); settings=one('SELECT * FROM settings WHERE id=1'); players=rows('SELECT * FROM players ORDER BY id DESC'); approved=rows("SELECT * FROM players WHERE status='approved' ORDER BY group_name,name"); pending=rows("SELECT * FROM players WHERE status='pending' ORDER BY id DESC"); matches=rows('SELECT m.*,p1.name n1,p2.name n2 FROM matches m LEFT JOIN players p1 ON p1.id=m.player1_id LEFT JOIN players p2 ON p2.id=m.player2_id ORDER BY m.id DESC'); table=standings(approved,matches)
    return render_template('admin.html',settings=settings,players=players,approved=approved,pending=pending,matches=matches,table=table,phases=PHASES,groups=GROUPS)

@app.route('/admin/player/<int:pid>',methods=['POST'])
@admin_required
def update_player(pid):
    action=request.form.get('action'); group=request.form.get('group','A')
    with engine.begin() as c:
        if action=='approve': c.execute(text("UPDATE players SET status='approved',group_name=:g WHERE id=:id"),{'g':group,'id':pid})
        elif action=='group' and group in GROUPS: c.execute(text('UPDATE players SET group_name=:g WHERE id=:id'),{'g':group,'id':pid})
        elif action=='delete': c.execute(text('DELETE FROM players WHERE id=:id'),{'id':pid})
    return redirect(url_for('admin'))

@app.route('/admin/settings',methods=['POST'])
@admin_required
def settings():
    phase=request.form.get('phase'); name=request.form.get('name','FC Championship').strip() or 'FC Championship'
    if phase not in PHASES: phase='Fase de Grupos'
    with engine.begin() as c: c.execute(text('UPDATE settings SET phase=:p,name=:n WHERE id=1'),{'p':phase,'n':name})
    return redirect(url_for('admin'))

@app.route('/admin/match',methods=['POST'])
@admin_required
def match():
    phase=request.form.get('phase'); group=request.form.get('group') or None; p1=request.form.get('p1');p2=request.form.get('p2')
    try: s1=int(request.form.get('s1'));s2=int(request.form.get('s2'))
    except: flash('Placar inválido.');return redirect(url_for('admin'))
    if not p1 or not p2 or p1==p2 or s1<0 or s2<0: flash('Confira jogadores e placar.');return redirect(url_for('admin'))
    with engine.begin() as c: c.execute(text('INSERT INTO matches(id,phase,group_name,player1_id,player2_id,score1,score2,played) VALUES(:id,:ph,:g,:a,:b,:s1,:s2,1)'),{'id':next_id(c,'matches'),'ph':phase,'g':group,'a':p1,'b':p2,'s1':s1,'s2':s2})
    return redirect(url_for('admin'))
@app.route('/admin/match/<int:mid>/delete',methods=['POST'])
@admin_required
def delete_match(mid):
    with engine.begin() as c:c.execute(text('DELETE FROM matches WHERE id=:id'),{'id':mid})
    return redirect(url_for('admin'))
@app.route('/health')
def health(): return {'status':'ok'}

init_db()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
