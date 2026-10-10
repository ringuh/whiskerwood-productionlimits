"""Generates the Blueprint paste text (T3D) for the ProductionLimits mod ("Production Limit Profiles") into tools/out/.
Usage: JMAP=path/to/Whiskerwood-x.jmap.gz python tools/pl_build.py

Assets (/Game/Mods/ProductionLimits/):
  BP_Startup        Actor        mod option
  BP_MapLoad        Actor        all logic
  WBP_LimitHelper   Widget BP, parent ProductionControls (the Production Limits window class) -> ReadState
  WBP_LimitWaiter   Widget BP, parent UserWidget, empty designer; event dispatcher Done
  WBP_LimitPanel    Widget BP, designer only: side panel; VerticalBox `List` (Is Variable)
  WBP_LimitButton   Widget BP, designer only: Button `Btn` -> TextBlock `Label` (both Is Variable)
  PAL_ProductionLimits Primary Asset Label

How the game does it (jmap 0.7.207, exe strings, FModel export of /Game/UI/ResourceRow_ProductionControl):
  - The Production Limits window = native ProductionControls (ArcoView), BP /Game/UI/ArcoViews/Arcoview_ProductionControls,
    opened by the HUD action "openProductionLimitControls". Its private BP-callable CalcState returns
    ProductionControlState_UI: m_resourcesByCategory_foods / _drygoods: Map<Name subcat, ResourceStockpileSubcategory
    {Slots: Map<Name resource, ResourceStockpileSlot{count, minHold = the limit}>}>, controlsUnlocked (administrator).
  - Each row (ResourceRow_ProductionControl) has a NumericControl whose hudAction default is "setProductionLimit"
    (resource in hudActionStringParam -> paramString) and a reset button that sends "clearProductionLimit"
    (built in the row graph, then HudAction on the row, i.e. it bubbles up row -> category -> window).
  - We send the same actions: HudAction on a category widget of the open window (same path as a click), with
    paramString = paramName = resource, paramInt = value. Fallback: ReceiveHudAction on the window.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pl_common import *

BUILD = 'v3'
TRACE = False
OUT = os.path.join(os.path.dirname(__file__), 'out')
os.makedirs(OUT, exist_ok=True)

STARTUP, MAPLOAD = M + 'BP_Startup', M + 'BP_MapLoad'
HELPER, WAITER, PANELW, QBTN = M + 'WBP_LimitHelper', M + 'WBP_LimitWaiter', M + 'WBP_LimitPanel', M + 'WBP_LimitButton'
VIEW, AWB, HUDW = PA + 'ProductionControls', PA + 'ArcoWidgetBase', PA + 'PlayHud'
STATE, SUBS, SLOT = PA + 'ProductionControlState_UI', PA + 'ResourceStockpileSubcategory', PA + 'ResourceStockpileSlot'
HUDA = PA + 'HudAction'
OPT_PANEL = 'ProductionLimits_Panel'
SET_ACTION, CLEAR_ACTION = 'setProductionLimit', 'clearProductionLimit'
PANEL_W = 230.0
GAP_PX = 22.0

# Built-in profiles. The user file ProductionLimitsConfig\ProductionLimits.txt is read after these, same format:
# a [section] with the same name replaces that profile completely, an empty one removes it, new names are added.
# PLACEHOLDER values until rinku's real lists are in.
INITIAL = [('*', 'off'),
                 # Raw Food
                 ('berries', '2500'), ('rawfish', '2500'), ('mushroom', '2500'), ('cannedfood', '100'),
                 # Cooked Food (Hardtack: no limit)
                 ('berrysoup', '900'), ('smokedfish', '900'), ('bread', '900'),
                 # Prepared Food
                 ('stew', '900'), ('fishskewers', '900'), ('jampastry', '900'),
                 # High Cuisine
                 ('heartymeal', '2500'), ('simplemeal', '2500'), ('platter', '2500'), ('advancedRations', '2500'),
                 # Refined Material (Cut Stone, Gold Bullion, Spices: no limit)
                 ('planks', '300'), ('thread', '300'), ('rope', '100'), ('fabric', '300'), ('copperbar', '300'),
                 ('bronze', '200'), ('ironbar', '900'), ('steel', '300'), ('flour', '300'), ('oil', '300'),
                 ('nails', '50'), ('steelplates', '50'),
                 # Supplies (Machinery: no limit)
                 ('fuel', '300'), ('simpleclothes', '300'), ('clothes', '900'), ('fertilizer', '900'), ('tablesalt', '300'),
                 ('salinesolution', '300'), ('medicine', '300'), ('bedding', '900'), ('furniture', '900'), ('soap', '0'),
                 ('fishingnet', '50'), ('vises', '50'), ('scissors', '50'), ('firetongs', '50'), ('ironpots', '50'),
                 ('precisionscales', '50'),
                 # Naval
                 ('sail', '50')]
# Midgame = Initial with these changes; Advanced = Midgame with every 900 -> 2500, then these
MID = {'cannedfood': '300', 'planks': '600', 'thread': '900', 'rope': '300', 'fabric': '900', 'copperbar': '500',
       'bronze': '500', 'flour': '900', 'oil': '900', 'spice': '2500', 'fuel': '900', 'fishingnet': '300'}
ADV = {'planks': '2500', 'rope': '900', 'fishingnet': '900', 'copperbar': '900', 'bronze': '900'}


def changed(base, changes, fn=lambda v: v):
    out = [(k, changes.get(k, fn(v))) for k, v in base]
    return out + [(k, v) for k, v in changes.items() if k not in dict(base)]


MIDGAME = changed(INITIAL, MID)
ADVANCED = changed(MIDGAME, ADV, lambda v: '2500' if v == '900' else v)
DEFAULT_PROFILES = [
    ('Initial', INITIAL),
    ('Midgame', MIDGAME),
    ('Advanced', ADVANCED),
    ('No limits', [('*', 'off')]),
]
DEFAULTS_TEXT = '|'.join(sum([['[%s]' % n] + ['%s = %s' % kv for kv in items] for n, items in DEFAULT_PROFILES], []))

STR_A, NAME_A, INT_A = ARR(STR), ARR(NAME), ARR(INT)
QBTN_CLS, QBTN_T = wbp_cls(QBTN), wbp_t(QBTN)
PANEL_CLS, PANEL_T = wbp_cls(PANELW), wbp_t(PANELW)
WAITER_CLS, WAITER_T = wbp_cls(WAITER), wbp_t(WAITER)
HELP_CLS, HELP_T = wbp_cls(HELPER), wbp_t(HELPER)
RES_IDS = ('wood,planks,stone,bricks,wheat,flour,spice,rawfish,mushroom,berries,bread,smokedfish,berrysoup,jampastry,stew,'
           'fishskewers,simplemeal,heartymeal,platter,cannedfood,basicRations,tea,finetea,tealeaves,flax,cotton,rope,fabric,'
           'fishingnet,sail,clothes,bedding,copperore,tinore,ironore,goldore,coal,rocksalt,potash,cobaltore,copperbar,bronze,'
           'ironbar,steel,goldbar,ruby,sapphire,emerald,amethyst,amber,obsidian,fuel,fertilizer,tablesalt,salinesolution,oil,'
           'medicine,soap,candles,nails,teaset,furniture,cannonframes,bronzecannons,handTool,steelplates,steelcannons,tools,'
           'trinkets,waste,peppers,mousetrap,diplomacySeals,thread,simpleclothes,advancedRations,vises,scissors,firetongs,'
           'ironpots,precisionscales,guano,stone_cannonball,iron_cannonball,bronze_cannonball,chainshot_cannonball')


def write(name, g):
    open(os.path.join(OUT, name + '.txt'), 'w', encoding='utf-8').write(g.text())


def retype(pin, t):
    keep = {k: pin.t[k] for k in ('ref', 'const')}
    pin.t = dict(t); pin.t.update(keep)


# =========================================================================== BP_Startup (Actor)
g = Graph(STARTUP)
bp = g.event('/Script/Engine.Actor', 'ReceiveBeginPlay', [], 'Begin', 0, 0)
vals = g.add(BG + 'K2Node_MakeArray', 'Vals0', ['NumInputs=2'], 300, 250)
vals.pin('Array', ARR(STR), out=True)
vals.pin('[0]', STR, default='On'); vals.pin('[1]', STR, default='Off')
reg = api_call(g, 'RegisterModOptions', 600, 0, name='Reg0', optionId=OPT_PANEL,
               optionDisplayName='Production Limit Profiles - profile list',
               DefaultValue='On',
               optionDescription='Shows the limit profiles (Initial, Midgame, Advanced and your own) beside the Production Limits '
                                 'window. Clicking one sets those limits. Edit them in Saved/mods/ProductionLimitsConfig/ProductionLimits.txt.')
link(vals['Array'], reg['Values']); ex(bp, reg)
write('BP_Startup', g)


# =========================================================================== WBP_LimitHelper (parent ProductionControls)
# Variables: Hud (Production Control State UI), Keys, SlotKeys, ItemNames (Name arrays), ItemCats (String array),
#            Limits (Integer array), Unlocked (Boolean)
# ReadState flattens CalcState into parallel arrays: ItemNames[i] in category ItemCats[i] has limit Limits[i] (minHold).
g = Graph(HELPER)
HUD_T = STRUCT(STATE)
ev = g.custom_event('ReadState', [], 0, 0)
cs = g.call(VIEW + ':CalcState', 'Compute', 250, 200)
sh = g.setv('Hud', HUD_T, 500, 0, name='SetHud'); link(cs['ReturnValue'], sh['Hud'])
if 'execute' in [p.name for p in cs.pins]:
    ex(ev, cs); ex(cs, sh)
else:
    ex(ev, sh)
prev = sh
for i, (var, t) in enumerate([('ItemNames', NAME), ('ItemCats', STR), ('Limits', INT)]):
    c = arrfn(g, 'Array_Clear', t, 750 + 250 * i, 0, 'Clear' + var, arr_pin=g.get(var, ARR(t), 700 + 250 * i, 200, name=var + 'GetC')[var])
    ex(prev, c); prev = c
hg = g.get('Hud', HUD_T, 1500, 250, name='HudGet')
bk = struct_node(g, 'Break', STATE, ['m_resourcesByCategory_foods', 'm_resourcesByCategory_drygoods', 'controlsUnlocked'], 1700, 250, 'BreakHud')
link(hg['Hud'], bk['ProductionControlState_UI'])
su = g.setv('Unlocked', BOOL, 1800, 0, name='SetUnlocked'); link(bk['controlsUnlocked'], su['Unlocked']); ex(prev, su)
prev, ppin = su, 'then'
MAP_T = MAP(NAME, STRUCT(SUBS))
SLOTMAP_T = MAP(NAME, STRUCT(SLOT))
for j, mp in enumerate(['m_resourcesByCategory_foods', 'm_resourcesByCategory_drygoods']):
    X0 = 2100 + 3000 * j; tg = 'F' if j == 0 else 'D'
    mk = g.call('/Script/Engine.BlueprintMapLibrary:Map_Keys', 'CategoryKeys' + tg, X0, 0)
    retype(mk['TargetMap'], MAP_T); retype(mk['Keys'], NAME_A)
    link(bk[mp], mk['TargetMap']); ex(prev, mk, ppin)
    sk = g.setv('Keys', NAME_A, X0 + 250, 0, name='SetKeys' + tg); link(mk['Keys'], sk['Keys']); ex(mk, sk)
    lp = foreach(g, g.get('Keys', NAME_A, X0 + 300, 200, name='KeysGet' + tg)['Keys'], NAME, X0 + 500, 0, 'CategoryLoop' + tg); ex(sk, lp, 'then', 'Exec')
    K = lp['Array Element']
    mf = g.call('/Script/Engine.BlueprintMapLibrary:Map_Find', 'FindCategory' + tg, X0 + 700, 250)
    retype(mf['TargetMap'], MAP_T); retype(mf['Key'], NAME); retype(mf['Value'], STRUCT(SUBS))
    link(bk[mp], mf['TargetMap']); link(K, mf['Key'])
    bs = struct_node(g, 'Break', SUBS, ['Slots'], X0 + 950, 250, 'BreakCategory' + tg); link(mf['Value'], bs['ResourceStockpileSubcategory'])
    msk = g.call('/Script/Engine.BlueprintMapLibrary:Map_Keys', 'ResourceKeys' + tg, X0 + 800, 0)
    retype(msk['TargetMap'], SLOTMAP_T); retype(msk['Keys'], NAME_A)
    link(bs['Slots'], msk['TargetMap']); ex(lp, msk, 'LoopBody')
    ssk = g.setv('SlotKeys', NAME_A, X0 + 1050, 0, name='SetSlotKeys' + tg); link(msk['Keys'], ssk['SlotKeys']); ex(msk, ssk)
    kraw = nstr(g, K, X0 + 1000, 400, 'CatKeyRaw' + tg)
    kst = g.call(KSTR + ':Replace', 'CatKeyStr' + tg, X0 + 1150, 400, From='subcat.', To='', SearchCase='IgnoreCase'); link(kraw, kst['SourceString'])
    lp2 = foreach(g, g.get('SlotKeys', NAME_A, X0 + 1250, 200, name='SlotKeysGet' + tg)['SlotKeys'], NAME, X0 + 1350, 0, 'ResourceLoop' + tg)
    ex(ssk, lp2, 'then', 'Exec')
    R = lp2['Array Element']
    ai = arrfn(g, 'Array_Add', NAME, X0 + 1600, 0, 'AddItem' + tg, arr_pin=g.get('ItemNames', NAME_A, X0 + 1550, 200, name='ItemNamesGetA' + tg)['ItemNames'], item_pin=R)
    ex(lp2, ai, 'LoopBody')
    aic = arrfn(g, 'Array_Add', STR, X0 + 1850, 0, 'AddItemCat' + tg, arr_pin=g.get('ItemCats', STR_A, X0 + 1800, 200, name='ItemCatsGetA' + tg)['ItemCats'], item_pin=kst['ReturnValue'])
    ex(ai, aic)
    sf = g.call('/Script/Engine.BlueprintMapLibrary:Map_Find', 'FindSlot' + tg, X0 + 1800, 450)
    retype(sf['TargetMap'], SLOTMAP_T); retype(sf['Key'], NAME); retype(sf['Value'], STRUCT(SLOT))
    link(bs['Slots'], sf['TargetMap']); link(R, sf['Key'])
    bsl = struct_node(g, 'Break', SLOT, ['minHold'], X0 + 2050, 450, 'BreakSlot' + tg); link(sf['Value'], bsl['ResourceStockpileSlot'])
    al = arrfn(g, 'Array_Add', INT, X0 + 2100, 0, 'AddLimit' + tg, arr_pin=g.get('Limits', INT_A, X0 + 2050, 200, name='LimitsGetA' + tg)['Limits'], item_pin=bsl['minHold'])
    ex(aic, al)
    prev, ppin = lp, 'Completed'
write('WBP_LimitHelper', g)


# =========================================================================== WBP_LimitWaiter (UserWidget, empty designer)
# Variables: Waited (Float), Stage (Integer). Event Dispatcher: Done (no inputs).
# While in the viewport it calls Done on its first tick, at 0.05 s and at 0.3 s (window open animation), then removes itself.
g = Graph(WAITER)
evT = g.event('/Script/UMG.UserWidget', 'Tick', [('MyGeometry', STRUCT('/Script/SlateCore.Geometry')), ('InDeltaTime', FLT)], 'Tick', 0, 0)
wg_ = g.get('Waited', DBL, 0, 250, name='WaitedGet')
add = g.call(KML + ':Add_DoubleDouble', 'AddDelta', 200, 250); link(wg_['Waited'], add['A']); link(evT['InDeltaTime'], add['B'])
sw = g.setv('Waited', DBL, 300, 0, name='SetWaited'); link(add['ReturnValue'], sw['Waited']); ex(evT, sw)
stg = g.get('Stage', INT, 400, 300, name='StageGet')
def call_done(x, y, name):
    n = g.add(BG + 'K2Node_CallDelegate', name, ['DelegateReference=(MemberName="Done",bSelfContext=True)'], x, y)
    n.pin('execute', EXEC); n.pin('then', EXEC, out=True); n.pin('self', T('object', obj=WAITER_CLS), friendly='NSLOCTEXT("K2Node", "Target", "Target")')
    return n
s0q = g.call(KML + ':EqualEqual_IntInt', 'IsStage0', 600, 300, B='0'); link(stg['Stage'], s0q['A'])
b0 = g.branch(600, 0, 'BrStage0'); link(s0q['ReturnValue'], b0['Condition']); ex(sw, b0)
st1 = g.setv('Stage', INT, 850, -200, value='1', name='ToStage1'); ex(b0, st1)
d0 = call_done(1100, -200, 'CallDoneFirst'); ex(st1, d0)
s1q = g.call(KML + ':EqualEqual_IntInt', 'IsStage1', 850, 300, B='1'); link(stg['Stage'], s1q['A'])
t1 = g.call(KML + ':GreaterEqual_DoubleDouble', 'After005', 850, 450, B='0.05'); link(sw['Output_Get'], t1['A'])
b1 = g.branch(850, 0, 'BrStage1'); link(andb(g, s1q['ReturnValue'], t1['ReturnValue'], 1050, 350, 'Stage1Due'), b1['Condition']); ex(b0, b1, 'else')
st2 = g.setv('Stage', INT, 1100, 100, value='2', name='ToStage2'); ex(b1, st2)
d1 = call_done(1350, 100, 'CallDoneSecond'); ex(st2, d1)
t2 = g.call(KML + ':GreaterEqual_DoubleDouble', 'After03', 1100, 450, B='0.3'); link(sw['Output_Get'], t2['A'])
b2 = g.branch(1100, 300, 'BrDone'); link(t2['ReturnValue'], b2['Condition']); ex(b1, b2, 'else')
r0 = g.setv('Waited', DBL, 1350, 300, value='0.0', name='ResetWaited'); ex(b2, r0)
r1 = g.setv('Stage', INT, 1600, 300, value='0', name='ResetStage'); ex(r0, r1)
rp = g.call('/Script/UMG.Widget:RemoveFromParent', 'Hide', 1850, 300); ex(r1, rp)
d2 = call_done(2100, 300, 'CallDoneLast'); ex(rp, d2)
write('WBP_LimitWaiter', g)


# =========================================================================== BP_MapLoad (Actor)
g = Graph(MAPLOAD)


def gv(var, t, x, y, tag=''):
    return g.get(var, t, x, y, name=var + 'Get' + tag)[var]


def sv(var, t, x, y, val_pin=None, value=None, tag=''):
    n = g.setv(var, t, x, y, value=value, name='Set' + var + tag)
    if val_pin is not None: link(val_pin, n[var])
    return n


def clear(var, t, x, y, tag=''):
    return arrfn(g, 'Array_Clear', t, x, y, 'Clear' + var + tag, arr_pin=gv(var, ARR(t), x - 50, y + 180, 'C' + tag))


def option_on(oid, x, y, tag):
    o = api_call(g, 'ReadModOptionValue', x, y, name='ReadOpt' + tag, optionId=oid, fallbackValue='On')
    return o, streq(g, o['ReturnValue'], 'On', x + 250, y + 200, 'OptOn' + tag)


def label(btn_pin, text_pin, x, y, tag, prev, prev_pin='then'):
    lb = bp_get(g, QBTN_CLS, 'Label', TXT_T, btn_pin, x, y + 200, 'LabelGet' + tag)
    tt = g.call(KTXT + ':Conv_StringToText', 'LabelText' + tag, x, y + 350)
    if isinstance(text_pin, str): tt.set('InString', text_pin)
    else: link(text_pin, tt['InString'])
    st = g.call('/Script/UMG.TextBlock:SetText', 'SetLabel' + tag, x + 250, y); link(lb['Label'], st['self']); link(tt['ReturnValue'], st['InText'])
    ex(prev, st, prev_pin)
    return st


def trim2(pin, x, y, name):
    return conv(g, 'TrimTrailing', conv(g, 'Trim', pin, x, y, name + 'L'), x + 150, y, name)


def strip_comment(pin, ch, x, y, tag):
    sp = g.call(KSTR + ':Split', 'CommentSplit' + tag, x, y, InStr=ch, SearchCase='IgnoreCase', SearchDir='FromStart'); link(pin, sp['SourceString'])
    sel = g.call(KML + ':SelectString', 'NoComment' + tag, x + 200, y); link(sp['LeftS'], sel['A']); link(pin, sel['B']); link(sp['ReturnValue'], sel['bPickA'])
    return sel['ReturnValue']


def bind_hud(prev, prev_pin, x, y, tag):
    """Find the PlayHud (top HUD widget, an ArcoWidgetBase) and listen to the HudActions its buttons send
    (e.g. openProductionLimitControls) -> OnHudSeen. Sets HudBound. Returns the exit knot."""
    ga = g.call('/Script/UMG.WidgetBlueprintLibrary:GetAllWidgetsOfClass', 'FindPlayHud' + tag, x, y, WidgetClass=HUDW, TopLevelOnly='false')
    ga['FoundWidgets'].t = ARR(UWT)
    link(self_node(g, x - 100, y + 200, 'MeHud' + tag)['self'], ga['WorldContextObject']); ex(prev, ga, prev_pin)
    lp = foreach(g, ga['FoundWidgets'], UWT, x + 250, y, 'PlayHudLoop' + tag); ex(ga, lp, 'then', 'Exec')
    ca = g.cast(AWB, False, x + 500, y, name='HudAsArco' + tag); link(lp['Array Element'], ca['Object']); ex(lp, ca, 'LoopBody')
    b = bind(g, MAPLOAD, ca['AsArcoWidgetBase'], AWB, 'OnHudActionDelegate', PKG('/Script/ProjectArco'), 'OnHudAction__DelegateSignature', evHS, x + 750, y, 'BindPlayHud' + tag)
    ex(ca, b)
    s = sv('HudBound', BOOL, x + 1000, y, value='true', tag=tag); ex(b, s)
    lH = log(g, x + 600, y - 300, msg_pin=concat(g, x + 600, y - 150, 'ProductionLimits: HUD listener ', tag, ', bound=',
                                                  bstr(g, gv('HudBound', BOOL, x + 400, y - 100, 'L' + tag), x + 500, y - 100, 'HudBoundStr' + tag)), name='LogHudBound' + tag)
    ex(lp, lH, 'Completed')
    return lH


# ---- BeginPlay -> onLoadingFinished (+ setup guard: a new game doesn't deliver onLoadingFinished to BP_MapLoad)
bp = g.event('/Script/Engine.Actor', 'ReceiveBeginPlay', [], 'Begin', 0, -4000)
api = modapi(g, 200, -3850, name='BindApi')
evL = g.custom_event('OnLoaded', [], 0, -3600)
evHS = g.custom_event('OnHudSeen', [('HudAction', STRUCT(HUDA))], 0, -1200)
b1 = bind(g, MAPLOAD, api['ReturnValue'], API, 'onLoadingFinished', PKG('/Script/SystemCore'), 'ModAPI_OnEvent__DelegateSignature', evL, 400, -4000, 'BindLoaded')
ex(bp, b1)
if TRACE:
    tr = api_call(g, 'LogMessage', 200, -4300, name='TraceBegin', doPrependDate='true', Msg='ProductionLimits TRACE BeginPlay')
    # (TRACE builds only) not wired into the chain to keep it simple

gr = g.branch(-300, -3300, 'BrReady'); link(g.get('Ready', BOOL, -450, -3150, name='ReadyGet')['Ready'], gr['Condition'])
ex(b1, gr); ex(evL, gr)
pcG = g.call('/Script/Engine.GameplayStatics:GetPlayerController', 'PCGuard', -300, -3000)
pcv = g.call(KSL + ':IsValid', 'PCGuardValid', -150, -3000); link(pcG['ReturnValue'], pcv['Object'])
gp = g.branch(-50, -3300, 'BrHavePC'); link(pcv['ReturnValue'], gp['Condition']); ex(gr, gp, 'else')
srd = g.setv('Ready', BOOL, 150, -3300, value='true', name='SetReady'); ex(gp, srd)
stg0 = g.get('SetupTries', INT, 0, -2800, name='SetupTriesGet')
stl = g.call(KML + ':Less_IntInt', 'SetupTriesLeft', 150, -2800, B='10'); link(stg0['SetupTries'], stl['A'])
bst = g.branch(150, -3000, 'BrSetupRetry'); link(stl['ReturnValue'], bst['Condition']); ex(gp, bst, 'else')
sta = g.call(KML + ':Add_IntInt', 'SetupTriesPlus', 300, -2850, B='1'); link(stg0['SetupTries'], sta['A'])
sst = g.setv('SetupTries', INT, 400, -3000, name='SetSetupTries'); link(sta['ReturnValue'], sst['SetupTries']); ex(bst, sst)
stm = g.call(KSL + ':K2_SetTimer', 'RetrySetup', 650, -3000, FunctionName='OnLoaded', Time='1.000000', bLooping='false')
link(self_node(g, 500, -2850, 'MeSetupTimer')['self'], stm['Object']); ex(sst, stm)

X, Y = 300, -3600
rdf = api_call(g, 'ReadModTextFile', X, Y, name='ReadDebugFile', modName=CFG, Filename='debug'); ex(srd, rdf)
dfe = g.call(KSTR + ':IsEmpty', 'DebugFileEmpty', X + 250, Y + 200); link(rdf['ReturnValue'], dfe['InString'])
sdb = sv('Debug', BOOL, X + 300, Y, notb(g, dfe['ReturnValue'], X + 450, Y + 200, 'DebugFileThere')); ex(rdf, sdb)
l0 = log(g, X + 700, Y, msg='ProductionLimits ready (%s)' % BUILD, name='LogReady'); ex(sdb, l0)
pc = g.call('/Script/Engine.GameplayStatics:GetPlayerController', 'PC', X + 900, Y + 250)
ei = g.call('/Script/Engine.Actor:EnableInput', 'EnableKeys', X + 1000, Y)
link(self_node(g, X + 900, Y + 150, 'MeInput')['self'], ei['self']); link(pc['ReturnValue'], ei['PlayerController']); ex(l0, ei)
prev = ei
for i, (asset, var, t) in enumerate([(HELPER, 'Helper', HELP_T), (PANELW, 'Panel', PANEL_T), (WAITER, 'Waiter', WAITER_T)]):
    cw = g.create_widget(asset, X + 1300 + 500 * i, Y, name='Create' + var); cw['ReturnValue'].t = t
    link(pc['ReturnValue'], cw['OwningPlayer']); ex(prev, cw)
    s = sv(var, t, X + 1550 + 500 * i, Y, cw['ReturnValue']); ex(cw, s); prev = s
evCC = g.custom_event('OnCheck', [], 0, -1000)
bw = bind(g, MAPLOAD, gv('Waiter', WAITER_T, X + 2800, Y + 200, 'B'), WAITER_CLS, 'Done',
          WAITER_CLS, 'Done__DelegateSignature', evCC, X + 2900, Y, 'BindWaiterDone', target_t=WAITER_T)
ex(prev, bw)
hb0 = bind_hud(bw, 'then', X + 3200, Y, 'Setup')

# ---- config: built-in profiles + user file, "|"-joined lines, one [section] per profile
X, Y = 300, -3000
rcf = api_call(g, 'ReadModTextFile', X, Y, name='ReadConfigFile', modName=CFG, Filename=MOD); link(hb0['then'], rcf['execute'])
rep = g.call(KSTR + ':Replace', 'NewlinesToBars', X + 250, Y + 200, From='\\n', To='|'); link(rcf['ReturnValue'], rep['SourceString'])
alltext = concat(g, X + 450, Y + 250, DEFAULTS_TEXT + '|', rep['ReturnValue'])
pia = g.call(KSTR + ':ParseIntoArray', 'SplitLines', X + 700, Y + 200, Delimiter='|', CullEmptyStrings='true'); link(alltext, pia['SourceString'])
sl = sv('Lines', STR_A, X + 300, Y, pia['ReturnValue']); ex(rcf, sl)
sc0 = sv('Cur', INT, X + 550, Y, value='-1', tag='Parse'); ex(sl, sc0)
prev = sc0
for i, var in enumerate(['PNames', 'PKeys', 'PItems', 'ProfileNames', 'ProfileItems']):
    c = clear(var, STR, X + 800 + 250 * i, Y); ex(prev, c); prev = c
c = clear('ProfileButtons', QBTN_T, X + 2050, Y); ex(prev, c); prev = c
X = 2600
lpL = foreach(g, gv('Lines', STR_A, X - 100, Y + 200, 'L'), STR, X, Y, 'LineLoop'); ex(prev, lpL, 'then', 'Exec')
LINE = strip_comment(strip_comment(lpL['Array Element'], ';', X - 300, Y + 600, 'Semi'), '#', X - 300, Y + 750, 'Hash')
L = clean(g, LINE, X + 50, Y + 300, 'LineClean')
le = g.call(KSTR + ':IsEmpty', 'LineEmpty', X + 500, Y + 400); link(L, le['InString'])
bSk = g.branch(X + 300, Y, 'BrSkipLine'); link(le['ReturnValue'], bSk['Condition']); ex(lpL, bSk, 'LoopBody')
bSec = g.branch(X + 550, Y, 'BrSection'); link(starts(g, L, '[', X + 550, Y + 500, 'IsSection'), bSec['Condition']); ex(bSk, bSec, 'else')
# [Name]: original case kept for the button
X, Y = 3500, -3600
body = g.call(KSTR + ':RightChop', 'DropBracket', X, Y + 300, count='1'); link(trim2(LINE, X - 300, Y + 300, 'SecTrim'), body['SourceString'])
spb = g.call(KSTR + ':Split', 'SplitBracket', X + 200, Y + 300, InStr=']', SearchCase='IgnoreCase', SearchDir='FromStart'); link(body['ReturnValue'], spb['SourceString'])
sel = g.call(KML + ':SelectString', 'SectionBody', X + 400, Y + 300); link(spb['LeftS'], sel['A']); link(body['ReturnValue'], sel['B']); link(spb['ReturnValue'], sel['bPickA'])
sName = sv('Value', STR, X + 200, Y, trim2(sel['ReturnValue'], X + 550, Y + 300, 'SecNameTrim'), tag='SecName'); ex(bSec, sName)
SECKEY = lower(g, sName['Output_Get'], X + 450, Y + 500, 'SecKey')
fk = arrfn(g, 'Array_Find', STR, X + 650, Y + 500, 'FindProfileKey', arr_pin=gv('PKeys', STR_A, X + 550, Y + 650, 'F'), item_pin=SECKEY)
sCur = sv('Cur', INT, X + 450, Y, fk['ReturnValue'], tag='Found'); ex(sName, sCur)
fge = g.call(KML + ':GreaterEqual_IntInt', 'ProfileKnown', X + 700, Y + 200, B='0'); link(sCur['Output_Get'], fge['A'])
bKn = g.branch(X + 700, Y, 'BrProfileKnown'); link(fge['ReturnValue'], bKn['Condition']); ex(sCur, bKn)
# known: start it over (replace)
rsI = arrfn(g, 'Array_Set', STR, X + 950, Y - 200, 'RestartProfile', arr_pin=gv('PItems', STR_A, X + 900, Y - 50, 'R'), idx_pin=gv('Cur', INT, X + 900, Y + 50, 'R'), item='')
ex(bKn, rsI)
# new: add
aN = arrfn(g, 'Array_Add', STR, X + 950, Y + 200, 'AddProfileName', arr_pin=gv('PNames', STR_A, X + 900, Y + 400, 'A'), item_pin=sName['Output_Get']); ex(bKn, aN, 'else')
aK = arrfn(g, 'Array_Add', STR, X + 1200, Y + 200, 'AddProfileKey', arr_pin=gv('PKeys', STR_A, X + 1150, Y + 400, 'A'), item_pin=SECKEY); ex(aN, aK)
aI = arrfn(g, 'Array_Add', STR, X + 1450, Y + 200, 'AddProfileItems', arr_pin=gv('PItems', STR_A, X + 1400, Y + 400, 'A'), item=''); ex(aK, aI)
sCurN = sv('Cur', INT, X + 1700, Y + 200, aI['ReturnValue'], tag='New'); ex(aI, sCurN)
# key = value
X, Y = 3500, -2600
spe = g.call(KSTR + ':Split', 'SplitEquals', X, Y + 300, InStr='=', SearchCase='IgnoreCase', SearchDir='FromStart'); link(LINE, spe['SourceString'])
KEY = clean(g, spe['LeftS'], X + 250, Y + 300, 'KeyClean')
VAL = clean(g, spe['RightS'], X + 250, Y + 450, 'ValClean')
ke = g.call(KSTR + ':IsEmpty', 'KeyEmpty', X + 700, Y + 300); link(KEY, ke['InString'])
inSec = g.call(KML + ':GreaterEqual_IntInt', 'InSection', X + 700, Y + 450, B='0'); link(gv('Cur', INT, X + 600, Y + 500, 'V'), inSec['A'])
okL = andb(g, andb(g, spe['ReturnValue'], notb(g, ke['ReturnValue'], X + 850, Y + 300, 'KeyThere'), X + 1000, Y + 300, 'HasKeyValue'), inSec['ReturnValue'], X + 1150, Y + 350, 'ValidLine')
bOk = g.branch(X + 300, Y, 'BrValidLine'); link(okL, bOk['Condition']); ex(bSec, bOk, 'else')
cu = gv('Cur', INT, X + 500, Y + 700, 'I')
newItems = concat(g, X + 800, Y + 700, item_at(g, gv('PItems', STR_A, X + 450, Y + 850, 'I'), STR, cu, X + 650, Y + 800, 'CurItems'), KEY, '=', VAL, ',')
ap = arrfn(g, 'Array_Set', STR, X + 1200, Y, 'AppendItem', arr_pin=gv('PItems', STR_A, X + 1100, Y + 200, 'S'), idx_pin=cu, item_pin=newItems); ex(bOk, ap)
# after parsing: keep the profiles that have lines
X, Y = 300, -2200
lpF = foreach(g, gv('PItems', STR_A, X - 100, Y + 200, 'F'), STR, X, Y, 'KeepLoop'); ex(lpL, lpF, 'Completed', 'Exec')
ie = g.call(KSTR + ':IsEmpty', 'ProfileEmpty', X + 250, Y + 300); link(lpF['Array Element'], ie['InString'])
bKe = g.branch(X + 300, Y, 'BrKeepProfile'); link(notb(g, ie['ReturnValue'], X + 400, Y + 300, 'ProfileHasLines'), bKe['Condition']); ex(lpF, bKe, 'LoopBody')
k1 = arrfn(g, 'Array_Add', STR, X + 550, Y, 'KeepName', arr_pin=gv('ProfileNames', STR_A, X + 500, Y + 200, 'K'),
           item_pin=item_at(g, gv('PNames', STR_A, X + 400, Y + 450, 'K'), STR, lpF['Array Index'], X + 550, Y + 450, 'KeptName')); ex(bKe, k1)
k2 = arrfn(g, 'Array_Add', STR, X + 800, Y, 'KeepItems', arr_pin=gv('ProfileItems', STR_A, X + 750, Y + 200, 'K'), item_pin=lpF['Array Element']); ex(k1, k2)
X, Y = 1500, -2200
fl = g.call(KSTR + ':Len', 'UserFileLen', X - 200, Y + 300); link(rcf['ReturnValue'], fl['S'])
pl = g.call(KSTR + ':JoinStringArray', 'ProfileList', X - 200, Y + 500, Separator=', '); link(gv('ProfileNames', STR_A, X - 400, Y + 550, 'J'), pl['SourceArray'])
lC = log(g, X, Y, msg_pin=concat(g, X, Y + 200, 'ProductionLimits: config ', istr(g, fl['ReturnValue'], X - 50, Y + 300, 'UserLenStr'),
                                 ' chars, profiles: ', pl['ReturnValue']), name='LogConfig')
ex(lpF, lC, 'Completed')
lpB = foreach(g, gv('ProfileNames', STR_A, X + 300, Y + 200, 'B'), STR, X + 350, Y, 'ProfileButtonLoop'); ex(lC, lpB, 'then', 'Exec')
cqb = g.create_widget(QBTN, X + 650, Y, name='CreateProfileButton'); cqb['ReturnValue'].t = QBTN_T
link(g.call('/Script/Engine.GameplayStatics:GetPlayerController', 'PC2', X + 500, Y + 250)['ReturnValue'], cqb['OwningPlayer']); ex(lpB, cqb, 'LoopBody')
lb1 = label(cqb['ReturnValue'], lpB['Array Element'], X + 950, Y, 'Profile', cqb)
lst = bp_get(g, PANEL_CLS, 'List', OBJ('/Script/UMG.VerticalBox'), gv('Panel', PANEL_T, X + 1150, Y + 300, 'L'), X + 1300, Y + 300, 'PanelListGet')
acp = g.call(PANEL + ':AddChild', 'AddProfileButton', X + 1450, Y); link(lst['List'], acp['self']); link(cqb['ReturnValue'], acp['Content']); ex(lb1, acp)
csl = g.cast('/Script/UMG.VerticalBoxSlot', False, X + 1700, Y, name='ProfileSlot'); link(acp['ReturnValue'], csl['Object']); ex(acp, csl)
spd = g.call('/Script/UMG.VerticalBoxSlot:SetPadding', 'PadProfileButton', X + 1950, Y, InPadding='(Left=0.000000,Top=2.000000,Right=0.000000,Bottom=2.000000)')
link(csl['AsVerticalBoxSlot'], spd['self']); ex(csl, spd)
evPC = g.custom_event('OnProfileClick', [], 0, 3000)
pbtn = bp_get(g, QBTN_CLS, 'Btn', BTN_T, cqb['ReturnValue'], X + 2000, Y + 300, 'ProfileBtnGet')
bpc = bind(g, MAPLOAD, pbtn['Btn'], '/Script/UMG.Button', 'OnClicked', PKG('/Script/UMG'), 'OnButtonClickedEvent__DelegateSignature', evPC, X + 2200, Y, 'BindProfileClick')
ex(spd, bpc); ex(csl, bpc, 'CastFailed')
apb = arrfn(g, 'Array_Add', QBTN_T, X + 2450, Y, 'AddProfileButtonRef', arr_pin=gv('ProfileButtons', ARR(QBTN_T), X + 2400, Y + 200, 'A'), item_pin=cqb['ReturnValue'])
ex(bpc, apb)

# ---- resource catalog from the game's Resources table (fallback when the window read is empty)
X, Y = 300, -1900
cid = g.call(KSTR + ':ParseIntoArray', 'SplitResourceIds', X, Y + 300, SourceString=RES_IDS, Delimiter=',', CullEmptyStrings='true')
sci = sv('CatIds', STR_A, X + 200, Y, cid['ReturnValue']); ex(lpB, sci, 'Completed')
pc_ = sci
for i_, (var, t_) in enumerate([('CatNames', NAME), ('CatItemCats', STR)]):
    c_ = clear(var, t_, X + 450 + 250 * i_, Y, 'T'); ex(pc_, c_); pc_ = c_
lpR = foreach(g, gv('CatIds', STR_A, X + 950, Y + 200, 'L'), STR, X + 1050, Y, 'ResourceIdLoop'); ex(pc_, lpR, 'then', 'Exec')
rid = g.call(KSTR + ':Conv_StringToName', 'ResourceRow', X + 1200, Y + 300); link(lpR['Array Element'], rid['InString'])
rdv = api_call(g, 'ReadDataTableValue', X + 1350, Y, name='ReadSubCategory', datatableName='Resources', ColumnName='subCategory')
link(rid['ReturnValue'], rdv['rowId']); ex(lpR, rdv, 'LoopBody')
scs = g.call(KSTR + ':Replace', 'SubCatNoPrefix', X + 1600, Y + 300, From='subcat.', To='', SearchCase='IgnoreCase'); link(rdv['ReturnValue'], scs['SourceString'])
sce = g.call(KSTR + ':IsEmpty', 'SubCatEmpty', X + 1800, Y + 400); link(scs['ReturnValue'], sce['InString'])
okc = andb(g, notb(g, sce['ReturnValue'], X + 1950, Y + 400, 'SubCatThere'),
           notb(g, streq(g, scs['ReturnValue'], 'None', X + 1800, Y + 500, 'SubCatNone'), X + 1950, Y + 500, 'SubCatNotNone'), X + 2100, Y + 450, 'SubCatOk')
bOkc = g.branch(X + 1650, Y, 'BrSubCatOk'); link(okc, bOkc['Condition']); ex(rdv, bOkc)
t1 = arrfn(g, 'Array_Add', NAME, X + 1900, Y, 'AddCatalogName', arr_pin=gv('CatNames', NAME_A, X + 1850, Y + 200, 'T'), item_pin=rid['ReturnValue']); ex(bOkc, t1)
t2 = arrfn(g, 'Array_Add', STR, X + 2150, Y, 'AddCatalogItemCat', arr_pin=gv('CatItemCats', STR_A, X + 2100, Y + 200, 'T'), item_pin=scs['ReturnValue']); ex(t1, t2)
lCt = log(g, X + 1300, Y - 400, msg_pin=concat(g, X + 1300, Y - 250, 'ProductionLimits: catalog from Resources table: ',
          istr(g, arrfn(g, 'Array_Length', NAME, X + 1100, Y - 200, 'CatalogCount', arr_pin=gv('CatNames', NAME_A, X + 1000, Y - 150, 'N'))['ReturnValue'], X + 1200, Y - 200, 'CatalogCountStr'),
          ' resources'), name='LogCatalog')
ex(lpR, lCt, 'Completed')

# ---- triggers: any key / mouse button released, a window button, or any HUD action -> waiter -> OnCheck
kA = g.add(BG + 'K2Node_InputKey', 'KeyAny', ['InputKey=AnyKey', 'bConsumeInput=False', 'bExecuteWhenPaused=True'], 0, -1600)
kA.pin('Pressed', EXEC, out=True); kA.pin('Released', EXEC, out=True); kA.pin('Key', STRUCT('/Script/InputCore.Key'), out=True)
evWB = g.custom_event('OnWindowButton', [], 0, -1400)
jn = knot(g, 250, -1500, 'InputJoin'); link(kA['Released'], jn['InputPin']); link(evWB['then'], jn['InputPin'])
bkS = struct_node(g, 'Break', HUDA, ['action', 'paramString', 'paramName', 'paramInt'], 200, -1000, 'BreakHudSeen')
link(evHS['HudAction'], bkS['HudAction'])
lHS = log(g, 300, -1250, msg_pin=concat(g, 450, -1000, 'ProductionLimits: HUD action ', bkS['action'], ' str=', bkS['paramString'],
                                        ' name=', nstr(g, bkS['paramName'], 350, -850, 'SeenHudName'), ' int=', istr(g, bkS['paramInt'], 350, -750, 'SeenHudInt')), name='LogHudSeen')
ex(evHS, lHS); link(lHS['then'], jn['InputPin'])
wtg = gv('Waiter', WAITER_T, 300, -1650, 'K')
inv = g.call('/Script/UMG.Widget:IsInViewport', 'WaiterShown', 500, -1650); link(wtg, inv['self'])
bk_ = g.branch(500, -1500, 'BrWaiterIdle'); link(inv['ReturnValue'], bk_['Condition']); link(jn['OutputPin'], bk_['execute'])
bwv = g.branch(750, -1500, 'BrWaiterValid'); link(is_valid(g, wtg, 700, -1350, 'WaiterValid'), bwv['Condition']); ex(bk_, bwv, 'else')
atv = g.call('/Script/UMG.UserWidget:AddToViewport', 'ShowWaiter', 1000, -1500); link(wtg, atv['self']); ex(bwv, atv)


# ---- reusable sections
def read_state(prev, prev_pin, x, y, tag):
    """Helper.ReadState (CalcState) -> ItemNames / ItemCats / Limits / Unlocked; empty -> catalog. Returns exit knot."""
    hp = gv('Helper', HELP_T, x, y + 250, 'RS' + tag)
    cw = g.cast(AWB, False, x, y, name='WinAsArco' + tag); link(gv('Win', UWT, x - 100, y + 200, 'RS' + tag), cw['Object']); ex(prev, cw, prev_pin)
    ctx = g.get('Context', OBJ('/Script/CoreUObject.Object'), x + 200, y + 400, owner=AWB, name='WinContext' + tag); link(cw['AsArcoWidgetBase'], ctx['self'])
    sc = g.call(KSL + ':SetObjectPropertyByName', 'HelperContext' + tag, x + 250, y, PropertyName='Context')
    link(hp, sc['Object']); link(ctx['Context'], sc['Value']); ex(cw, sc)
    rs = bp_call(g, HELP_CLS, 'ReadState', hp, x + 500, y, 'ReadState' + tag); ex(sc, rs)
    ex(cw, rs, 'CastFailed')
    p = rs
    for k, (v2, t2) in enumerate([('ItemNames', NAME_A), ('ItemCats', STR_A), ('Limits', INT_A), ('Unlocked', BOOL)]):
        hv = bp_get(g, HELP_CLS, v2, t2, hp, x + 700 + 250 * k, y + 250, 'H%s%s' % (v2, tag))
        s = sv(v2, t2, x + 750 + 250 * k, y, hv[v2], tag=tag); ex(p, s); p = s
    n = arrfn(g, 'Array_Length', NAME, x + 1800, y + 300, 'ItemCount' + tag, arr_pin=gv('ItemNames', NAME_A, x + 1700, y + 400, 'RSN' + tag))
    has = g.call(KML + ':Greater_IntInt', 'HasItems' + tag, x + 1950, y + 300, B='0'); link(n['ReturnValue'], has['A'])
    bH = g.branch(x + 1800, y, 'BrHasItems' + tag); link(has['ReturnValue'], bH['Condition']); ex(p, bH)
    fin = knot(g, x + 3200, y, 'StateReady' + tag)
    link(bH['then'], fin['InputPin'])
    p = bH; pp = 'else'
    for k, (dst, src, t2) in enumerate([('ItemNames', 'CatNames', NAME_A), ('ItemCats', 'CatItemCats', STR_A)]):
        s_ = sv(dst, t2, x + 2050 + 250 * k, y + 300, gv(src, t2, x + 2000 + 250 * k, y + 500, 'UC' + tag), tag='UC' + tag); ex(p, s_, pp); p = s_; pp = 'then'
    cL = clear('Limits', INT, x + 2600, y + 300, 'UC' + tag); ex(p, cL)
    lU = log(g, x + 2900, y + 300, msg='ProductionLimits:   window read is empty, using the catalog', name='LogUseCatalog' + tag); ex(cL, lU)
    link(lU['then'], fin['InputPin'])
    return fin


def hovered_index(prev, prev_pin, arr_var, x, y, tag):
    """Sel = index of the button in arr_var whose Btn is hovered (the one just clicked), else -1."""
    s0 = sv('Sel', INT, x, y, value='-1', tag='H' + tag); ex(prev, s0, prev_pin)
    lp = foreach(g, gv(arr_var, ARR(QBTN_T), x + 200, y + 200, 'H' + tag), QBTN_T, x + 250, y, 'HoverLoop' + tag); ex(s0, lp, 'then', 'Exec')
    b = bp_get(g, QBTN_CLS, 'Btn', BTN_T, lp['Array Element'], x + 450, y + 250, 'HoverBtn' + tag)
    ih = g.call('/Script/UMG.Widget:IsHovered', 'IsHovered' + tag, x + 650, y + 250); link(b['Btn'], ih['self'])
    bH = g.branch(x + 550, y, 'BrHovered' + tag); link(ih['ReturnValue'], bH['Condition']); ex(lp, bH, 'LoopBody')
    s1 = sv('Sel', INT, x + 800, y, lp['Array Index'], tag='Hit' + tag); ex(bH, s1)
    ok = g.call(KML + ':GreaterEqual_IntInt', 'GotButton' + tag, x + 600, y + 500, B='0'); link(gv('Sel', INT, x + 450, y + 500, 'G' + tag), ok['A'])
    bOk = g.branch(x + 800, y + 400, 'BrGotButton' + tag); link(ok['ReturnValue'], bOk['Condition']); ex(lp, bOk, 'Completed')
    lN = log(g, x + 1050, y + 600, msg='ProductionLimits: click, but no hovered button found', name='LogNoHover' + tag); ex(bOk, lN, 'else')
    return bOk


# ---- OnCheck: is the Production Limits window open?
X, Y = 300, -1000
sw0 = sv('Win', UWT, X, Y, value=None, tag='Clear'); ex(evCC, sw0)
bHB = g.branch(X + 200, Y - 400, 'BrHudBound'); link(gv('HudBound', BOOL, X + 100, Y - 250, 'C'), bHB['Condition']); ex(sw0, bHB)
hb1 = bind_hud(bHB, 'else', X + 400, Y - 700, 'Retry')
cj = knot(g, X + 1700, Y - 400, 'HudChecked'); link(bHB['then'], cj['InputPin']); link(hb1['then'], cj['InputPin'])
ga = g.call('/Script/UMG.WidgetBlueprintLibrary:GetAllWidgetsOfClass', 'AllLimitWindows', X + 1900, Y, WidgetClass=VIEW, TopLevelOnly='false')
ga['FoundWidgets'].t = ARR(UWT)
link(self_node(g, X + 1800, Y + 200, 'MeWC')['self'], ga['WorldContextObject']); link(cj['OutputPin'], ga['execute'])
lpW = foreach(g, ga['FoundWidgets'], UWT, X + 2150, Y, 'WindowLoop'); ex(ga, lpW, 'then', 'Exec')
W = lpW['Array Element']
notH = g.call(KML + ':NotEqual_ObjectObject', 'NotHelper', X + 2350, Y + 250); link(W, notH['A']); link(gv('Helper', HELP_T, X + 2200, Y + 350, 'W'), notH['B'])
vis = g.call('/Script/UMG.Widget:IsVisible', 'WinVisible', X + 2350, Y + 400); link(W, vis['self'])
bW = g.branch(X + 2400, Y, 'BrIsWindow'); link(andb(g, notH['ReturnValue'], vis['ReturnValue'], X + 2550, Y + 300, 'VisibleWindow'), bW['Condition'])
ex(lpW, bW, 'LoopBody')
s1 = sv('Win', UWT, X + 2650, Y, W, tag='Found'); ex(bW, s1)

X, Y = 3400, -1000
wv = is_valid(g, gv('Win', UWT, X, Y + 200, 'V'), X + 150, Y + 200, 'WinValid')
bV = g.branch(X + 200, Y, 'BrWindowOpen'); link(wv, bV['Condition']); ex(lpW, bV, 'Completed')
# no window: hide the panel, forget the window
pnl = gv('Panel', PANEL_T, X + 300, Y + 700, 'H')
pin_ = g.call('/Script/UMG.Widget:IsInViewport', 'PanelShown', X + 500, Y + 700); link(pnl, pin_['self'])
sIn0 = sv('Injected', UWT, X + 300, Y + 500, value=None, tag='Closed'); ex(bV, sIn0, 'else')
bPS = g.branch(X + 550, Y + 500, 'BrPanelShown'); link(pin_['ReturnValue'], bPS['Condition']); ex(sIn0, bPS)
rpp = g.call('/Script/UMG.Widget:RemoveFromParent', 'HidePanel', X + 800, Y + 500); link(pnl, rpp['self']); ex(bPS, rpp)
newW = g.call(KML + ':NotEqual_ObjectObject', 'NewWindow', X + 450, Y + 250); link(gv('Win', UWT, X + 300, Y + 300, 'N'), newW['A']); link(gv('Injected', UWT, X + 300, Y + 400, 'N'), newW['B'])
bN = g.branch(X + 450, Y, 'BrNewWindow'); link(newW['ReturnValue'], bN['Condition']); ex(bV, bN)
posJ = knot(g, X + 9000, Y, 'PositionPanel')
link(bN['else'], posJ['InputPin'])

# new window: remember it, bind its buttons (close etc.) -> re-check
X, Y = 4200, -1000
si = sv('Injected', UWT, X, Y, gv('Win', UWT, X - 100, Y + 200, 'I')); ex(bN, si)
sLX = sv('LastX', DBL, X + 250, Y, value='-100000.0', tag='New'); ex(si, sLX)
lW = log(g, X + 550, Y, msg_pin=concat(g, X + 450, Y + 200, 'ProductionLimits: Production Limits window opened: ', nm(g, gv('Win', UWT, X + 250, Y + 300, 'L'), X + 350, Y + 300, 'WinName'),
                                       ' [', clsname(g, gv('Win', UWT, X + 250, Y + 400, 'L2'), X + 350, Y + 400, 'WinClass'), ']'), name='LogNewWin')
ex(sLX, lW)
fdB = descendants(g, gv('Win', UWT, X + 700, Y + 300, 'B'), ['/Script/UMG.Button'], X + 800, Y + 200, 'WindowButtons')
ex(lW, fdB)
lpWB = foreach(g, fdB['ReturnValue'], WIDGET_T, X + 1100, Y, 'WindowButtonLoop'); ex(fdB, lpWB, 'then', 'Exec')
cbt = g.cast('/Script/UMG.Button', False, X + 1350, Y, name='AsGameButton'); link(lpWB['Array Element'], cbt['Object']); ex(lpWB, cbt, 'LoopBody')
bWB = bind(g, MAPLOAD, cbt['AsButton'], '/Script/UMG.Button', 'OnClicked', PKG('/Script/UMG'), 'OnButtonClickedEvent__DelegateSignature', evWB, X + 1600, Y, 'BindWindowButton')
ex(cbt, bWB)

# ---- debug only: current limits as config lines + spy on what the window's widgets send (confirms action params)
X, Y = 6200, -1000
bDbg = g.branch(X, Y, 'BrDebugDump'); link(gv('Debug', BOOL, X - 100, Y + 200, 'Q'), bDbg['Condition']); ex(lpWB, bDbg, 'Completed')
rsD = read_state(bDbg, 'then', X + 250, Y, 'Dump')
lD0 = log(g, X + 3600, Y, msg_pin=concat(g, X + 3550, Y + 200, 'ProductionLimits: current limits (', istr(g, arrfn(g, 'Array_Length', NAME, X + 3300, Y + 300, 'DumpCount', arr_pin=gv('ItemNames', NAME_A, X + 3200, Y + 350, 'DC'))['ReturnValue'], X + 3450, Y + 300, 'DumpCountStr'),
                                          ' resources, unlocked=', bstr(g, gv('Unlocked', BOOL, X + 3300, Y + 450, 'D'), X + 3450, Y + 450, 'UnlockedStr'), ') as a profile:'), name='LogDumpHead')
link(rsD['OutputPin'], lD0['execute'])
lpD = foreach(g, gv('ItemNames', NAME_A, X + 3900, Y + 200, 'D'), NAME, X + 4000, Y, 'DumpLoop'); ex(lD0, lpD, 'then', 'Exec')
nl = arrfn(g, 'Array_Length', INT, X + 4050, Y + 600, 'LimitCountD', arr_pin=gv('Limits', INT_A, X + 3950, Y + 650, 'DL'))
hasL = g.call(KML + ':Less_IntInt', 'HasLimitD', X + 4200, Y + 550); link(lpD['Array Index'], hasL['A']); link(nl['ReturnValue'], hasL['B'])
limS = g.call(KML + ':SelectString', 'LimitOrUnknown', X + 4400, Y + 450, B='?')
link(istr(g, item_at(g, gv('Limits', INT_A, X + 4050, Y + 450, 'DV'), INT, lpD['Array Index'], X + 4200, Y + 400, 'LimitAt'), X + 4300, Y + 350, 'LimitStr'), limS['A'])
link(hasL['ReturnValue'], limS['bPickA'])
lD1 = log(g, X + 4300, Y, msg_pin=concat(g, X + 4600, Y + 200, 'ProductionLimits:   ', nstr(g, lpD['Array Element'], X + 4250, Y + 250, 'DumpRes'), ' = ', limS['ReturnValue'],
                                          '   ; @', item_at(g, gv('ItemCats', STR_A, X + 4300, Y + 650, 'DC2'), STR, lpD['Array Index'], X + 4450, Y + 650, 'DumpCat')), name='LogDumpLine')
ex(lpD, lD1, 'LoopBody')
evSpy = g.custom_event('OnSeenWindowAction', [('HudAction', STRUCT(HUDA))], 0, 6000)
fdA = descendants(g, gv('Win', UWT, X + 4700, Y + 300, 'A'), [AWB], X + 4800, Y + 200, 'WindowArcoWidgets')
ex(lpD, fdA, 'Completed')
sAr = sv('Arcos', ARR(WIDGET_T), X + 5000, Y, fdA['ReturnValue']); ex(fdA, sAr)
lpA = foreach(g, gv('Arcos', ARR(WIDGET_T), X + 5050, Y + 200, 'L'), WIDGET_T, X + 5150, Y, 'SpyLoop'); ex(sAr, lpA, 'then', 'Exec')
caS = g.cast(AWB, False, X + 5400, Y, name='AsArcoForSpy'); link(lpA['Array Element'], caS['Object']); ex(lpA, caS, 'LoopBody')
bSp = bind(g, MAPLOAD, caS['AsArcoWidgetBase'], AWB, 'OnHudActionDelegate', PKG('/Script/ProjectArco'), 'OnHudAction__DelegateSignature', evSpy, X + 5650, Y, 'BindSpy')
ex(caS, bSp)
lSp = log(g, X + 5300, Y - 400, msg_pin=concat(g, X + 5300, Y - 250, 'ProductionLimits:   spying on ', istr(g, arrfn(g, 'Array_Length', WIDGET_T, X + 5100, Y - 200, 'SpyCount', arr_pin=gv('Arcos', ARR(WIDGET_T), X + 5000, Y - 150, 'N'))['ReturnValue'], X + 5200, Y - 200, 'SpyCountStr'), ' window widgets'), name='LogSpy')
ex(lpA, lSp, 'Completed')
link(lSp['then'], posJ['InputPin']); link(bDbg['else'], posJ['InputPin'])
bkA = struct_node(g, 'Break', HUDA, ['action', 'paramString', 'paramName', 'paramInt', 'paramFloat', 'paramBool'], 300, 6250, 'BreakSeen')
link(evSpy['HudAction'], bkA['HudAction'])
lHA = log(g, 600, 6000, msg_pin=concat(g, 550, 6200, 'ProductionLimits SEEN window action: ', bkA['action'], ' str=', bkA['paramString'], ' name=', nstr(g, bkA['paramName'], 450, 6500, 'SeenName'),
                                       ' int=', istr(g, bkA['paramInt'], 450, 6600, 'SeenInt'), ' float=', conv(g, 'Conv_DoubleToString', bkA['paramFloat'], 450, 6700, 'SeenFloat'),
                                       ' bool=', bstr(g, bkA['paramBool'], 450, 6800, 'SeenBool')), name='LogSeen')
ex(evSpy, lHA)

# ---- position the panel next to the window (option)
X, Y = 13000, -1000
oP, onP = option_on(OPT_PANEL, X, Y, 'Panel')
link(posJ['OutputPin'], oP['execute'])
hasP = g.call(KML + ':Greater_IntInt', 'HasProfiles', X + 250, Y + 400, B='0')
link(arrfn(g, 'Array_Length', STR, X + 100, Y + 400, 'ProfileCountP', arr_pin=gv('ProfileNames', STR_A, X, Y + 450, 'P'))['ReturnValue'], hasP['A'])
bPo = g.branch(X + 300, Y, 'BrShowPanel'); link(andb(g, onP, hasP['ReturnValue'], X + 450, Y + 300, 'ShowPanel'), bPo['Condition']); ex(oP, bPo)
pnl2 = gv('Panel', PANEL_T, X + 400, Y + 600, 'P')
inv2 = g.call('/Script/UMG.Widget:IsInViewport', 'PanelInViewport', X + 600, Y + 600); link(pnl2, inv2['self'])
bIn = g.branch(X + 550, Y, 'BrPanelAdded'); link(inv2['ReturnValue'], bIn['Condition']); ex(bPo, bIn)
atp = g.call('/Script/UMG.UserWidget:AddToViewport', 'ShowPanel', X + 800, Y + 150, ZOrder='50'); link(pnl2, atp['self']); ex(bIn, atp, 'else')
pj = knot(g, X + 1050, Y, 'PanelReady'); link(bIn['then'], pj['InputPin']); link(atp['then'], pj['InputPin'])
fdS = descendants(g, gv('Win', UWT, X + 1000, Y - 100, 'S'), ['/Script/UMG.ScrollBox'], X + 1150, Y - 300, 'WindowScrollBoxes')
link(pj['OutputPin'], fdS['execute'])
gai = g.add(BG + 'K2Node_GetArrayItem', 'FirstScrollBox', ['bReturnByRefDesired=False'], X + 650, Y + 300)
_at = ARR(WIDGET_T); _at['ref'] = True; _at['const'] = True
gai.pin('Array', _at); gai.pin('Dimension 1', INT, default='0'); gai.pin('Output', WIDGET_T, out=True)
link(fdS['ReturnValue'], gai['Array']); sb0 = gai['Output']
gotS = g.call(KML + ':Greater_IntInt', 'HasScrollBox', X + 650, Y + 450, B='0')
link(arrfn(g, 'Array_Length', WIDGET_T, X + 500, Y + 450, 'ScrollBoxCount', arr_pin=fdS['ReturnValue'])['ReturnValue'], gotS['A'])
anchor = g.call(KML + ':SelectObject', 'PlacementAnchor', X + 800, Y + 350); link(sb0, anchor['A']); link(gv('Win', UWT, X + 650, Y + 550, 'G'), anchor['B']); link(gotS['ReturnValue'], anchor['bSelectA'])
caA = g.cast('/Script/UMG.Widget', False, X + 1300, Y - 300, name='AnchorAsWidget'); link(anchor['ReturnValue'], caA['Object']); ex(fdS, caA)
geo = g.call('/Script/UMG.Widget:GetCachedGeometry', 'WinGeometry', X + 900, Y + 400); link(caA['AsWidget'], geo['self'])
me = self_node(g, X + 900, Y + 550, 'MeGeo')['self']
tl = g.call('/Script/UMG.SlateBlueprintLibrary:LocalToViewport', 'WinTopLeft', X + 1150, Y + 400); link(me, tl['WorldContextObject']); link(geo['ReturnValue'], tl['Geometry'])
lsz = g.call('/Script/UMG.SlateBlueprintLibrary:GetLocalSize', 'WinSize', X + 1150, Y + 700); link(geo['ReturnValue'], lsz['Geometry'])
bsz = g.call(KML + ':BreakVector2D', 'WinSizeXY', X + 1350, Y + 700); link(lsz['ReturnValue'], bsz['InVec'])
mtr = g.call(KML + ':MakeVector2D', 'TopRightLocal', X + 1550, Y + 700, Y='0.0'); link(bsz['X'], mtr['X'])
tr = g.call('/Script/UMG.SlateBlueprintLibrary:LocalToViewport', 'WinTopRight', X + 1750, Y + 600); link(me, tr['WorldContextObject']); link(geo['ReturnValue'], tr['Geometry']); link(mtr['ReturnValue'], tr['LocalCoordinate'])
btl = g.call(KML + ':BreakVector2D', 'TopLeftXY', X + 1400, Y + 400); link(tl['PixelPosition'], btl['InVec'])
btr = g.call(KML + ':BreakVector2D', 'TopRightXY', X + 1950, Y + 600); link(tr['PixelPosition'], btr['InVec'])
need = g.call(KML + ':Multiply_DoubleDouble', 'PanelWidthPx', X + 1750, Y + 900, A='1.0', B=str(PANEL_W * 1.5 + GAP_PX))
roomL = g.call(KML + ':Greater_DoubleDouble', 'RoomOnLeft', X + 1950, Y + 900); link(btl['X'], roomL['A']); link(need['ReturnValue'], roomL['B'])
gap = g.call(KML + ':Multiply_DoubleDouble', 'GapPx', X + 1750, Y + 1050, A='1.0', B=str(GAP_PX))
same = g.call(KML + ':NearlyEqual_FloatFloat', 'SamePlace', X + 1600, Y - 500, ErrorTolerance='0.5'); link(btl['X'], same['A']); link(gv('LastX', DBL, X + 1450, Y - 450, 'M'), same['B'])
bMv = g.branch(X + 1500, Y - 700, 'BrWindowMoving'); link(notb(g, same['ReturnValue'], X + 1750, Y - 500, 'StillMoving'), bMv['Condition']); ex(caA, bMv)
sLX2 = sv('LastX', DBL, X + 1750, Y - 900, btl['X'], tag='Moving'); ex(bMv, sLX2)
hdM = g.call('/Script/UMG.Widget:RemoveFromParent', 'HidePanelWhileMoving', X + 2000, Y - 900); link(pnl2, hdM['self']); ex(sLX2, hdM)
wtM = gv('Waiter', WAITER_T, X + 2000, Y - 700, 'M')
iwM = g.call('/Script/UMG.Widget:IsInViewport', 'WaiterBusy', X + 2200, Y - 700); link(wtM, iwM['self'])
bWM = g.branch(X + 2250, Y - 900, 'BrWaiterBusyM'); link(iwM['ReturnValue'], bWM['Condition']); ex(hdM, bWM)
awM = g.call('/Script/UMG.UserWidget:AddToViewport', 'LookAgain', X + 2500, Y - 900); link(wtM, awM['self']); ex(bWM, awM, 'else')
bL = g.branch(X + 1300, Y, 'BrRoomLeft'); link(roomL['ReturnValue'], bL['Condition']); ex(bMv, bL, 'else')
xl = g.call(KML + ':Subtract_DoubleDouble', 'LeftX', X + 2150, Y + 400); link(btl['X'], xl['A']); link(gap['ReturnValue'], xl['B'])
pl_ = g.call(KML + ':MakeVector2D', 'LeftPos', X + 2350, Y + 400); link(xl['ReturnValue'], pl_['X']); link(btl['Y'], pl_['Y'])
al = g.call(UW + ':SetAlignmentInViewport', 'AlignRight', X + 1600, Y - 200, Alignment='(X=1.000000,Y=0.000000)'); link(pnl2, al['self']); ex(bL, al)
spl_ = g.call(UW + ':SetPositionInViewport', 'PlaceLeft', X + 1850, Y - 200, bRemoveDPIScale='true'); link(pnl2, spl_['self']); link(pl_['ReturnValue'], spl_['position']); ex(al, spl_)
xr = g.call(KML + ':Add_DoubleDouble', 'RightX', X + 2150, Y + 600); link(btr['X'], xr['A']); link(gap['ReturnValue'], xr['B'])
pr = g.call(KML + ':MakeVector2D', 'RightPos', X + 2350, Y + 600); link(xr['ReturnValue'], pr['X']); link(btr['Y'], pr['Y'])
ar = g.call(UW + ':SetAlignmentInViewport', 'AlignLeft', X + 1600, Y + 100, Alignment='(X=0.000000,Y=0.000000)'); link(pnl2, ar['self']); ex(bL, ar, 'else')
spr = g.call(UW + ':SetPositionInViewport', 'PlaceRight', X + 1850, Y + 100, bRemoveDPIScale='true'); link(pnl2, spr['self']); link(pr['ReturnValue'], spr['position']); ex(ar, spr)
pin3 = g.call('/Script/UMG.Widget:IsInViewport', 'PanelShownOff', X + 600, Y + 1200); link(pnl2, pin3['self'])
bOff = g.branch(X + 550, Y + 1000, 'BrPanelOffShown'); link(pin3['ReturnValue'], bOff['Condition']); ex(bPo, bOff, 'else')
rp3 = g.call('/Script/UMG.Widget:RemoveFromParent', 'HidePanelOff', X + 800, Y + 1000); link(pnl2, rp3['self']); ex(bOff, rp3)
ww = g.call(KML + ':Subtract_DoubleDouble', 'WinWidthPx', X + 2100, Y + 200); link(btr['X'], ww['A']); link(btl['X'], ww['B'])
lPos = log(g, X + 2400, Y - 200, msg_pin=concat(g, X + 2400, Y - 50, 'ProductionLimits:   panel placed, window at x=',
                                                conv(g, 'Conv_DoubleToString', btl['X'], X + 2200, Y, 'WinXStr'), ' y=',
                                                conv(g, 'Conv_DoubleToString', btl['Y'], X + 2200, Y + 100, 'WinYStr'), ' width px=',
                                                conv(g, 'Conv_DoubleToString', ww['ReturnValue'], X + 2250, Y + 200, 'WinWStr'),
                                                ' left=', bstr(g, roomL['ReturnValue'], X + 2200, Y + 300, 'LeftStr')), name='LogPlaced')
link(spl_['then'], lPos['execute']); link(spr['then'], lPos['execute'])


# ---- OnProfileClick: which profile -> expand its lines into WantNames / WantVals -> send the actions
X, Y = 300, 3000
hiP = hovered_index(evPC, 'then', 'ProfileButtons', X, Y, 'Profile')
rsP = read_state(hiP, 'then', X + 1300, Y, 'Profile')
X = 4900
items = item_at(g, gv('ProfileItems', STR_A, X, Y + 300, 'V'), STR, gv('Sel', INT, X, Y + 400, 'V'), X + 200, Y + 300, 'ProfileValue')
sVal = sv('Value', STR, X + 200, Y, items, tag='Profile'); link(rsP['OutputPin'], sVal['execute'])
cwn = clear('WantNames', NAME, X + 450, Y, 'P'); ex(sVal, cwn)
cwv = clear('WantVals', STR, X + 700, Y, 'P'); ex(cwn, cwv)
tok = g.call(KSTR + ':ParseIntoArray', 'SplitTokens', X + 750, Y + 300, Delimiter=',', CullEmptyStrings='true'); link(gv('Value', STR, X + 600, Y + 400, 'T'), tok['SourceString'])
sTk = sv('Tokens', STR_A, X + 950, Y, tok['ReturnValue']); ex(cwv, sTk)
lpK = foreach(g, gv('Tokens', STR_A, X + 1050, Y + 200, 'L'), STR, X + 1200, Y, 'TokenLoop'); ex(sTk, lpK, 'then', 'Exec')
spk = g.call(KSTR + ':Split', 'SplitToken', X + 1300, Y + 400, InStr='=', SearchCase='IgnoreCase', SearchDir='FromStart'); link(lpK['Array Element'], spk['SourceString'])
sTK = sv('TokKey', STR, X + 1450, Y, spk['LeftS']); ex(lpK, sTK, 'LoopBody')
sTV = sv('TokVal', STR, X + 1700, Y, spk['RightS']); ex(sTK, sTV)
TK = sTK['Output_Get']


def put(prev, prev_pin, res_pin, x, y, tag):
    """WantNames/WantVals: res -> TokVal (a later line wins). Returns the last node (its 'then' continues)."""
    f = arrfn(g, 'Array_Find', NAME, x, y + 300, 'FindWant' + tag, arr_pin=gv('WantNames', NAME_A, x - 100, y + 450, 'F' + tag), item_pin=res_pin)
    s = sv('Idx', INT, x, y, f['ReturnValue'], tag='Put' + tag); ex(prev, s, prev_pin)
    ge = g.call(KML + ':GreaterEqual_IntInt', 'WantKnown' + tag, x + 250, y + 300, B='0'); link(s['Output_Get'], ge['A'])
    b = g.branch(x + 250, y, 'BrWantKnown' + tag); link(ge['ReturnValue'], b['Condition']); ex(s, b)
    j = knot(g, x + 1100, y, 'Put' + tag + 'Done')
    st = arrfn(g, 'Array_Set', STR, x + 500, y - 200, 'ReplaceWant' + tag, arr_pin=gv('WantVals', STR_A, x + 450, y - 50, 'S' + tag),
               idx_pin=gv('Idx', INT, x + 450, y + 50, 'S' + tag), item_pin=gv('TokVal', STR, x + 450, y + 150, 'S' + tag)); ex(b, st)
    a1 = arrfn(g, 'Array_Add', NAME, x + 500, y + 200, 'AddWantName' + tag, arr_pin=gv('WantNames', NAME_A, x + 450, y + 400, 'A' + tag), item_pin=res_pin); ex(b, a1, 'else')
    a2 = arrfn(g, 'Array_Add', STR, x + 750, y + 200, 'AddWantVal' + tag, arr_pin=gv('WantVals', STR_A, x + 700, y + 400, 'A' + tag),
               item_pin=gv('TokVal', STR, x + 650, y + 500, 'A' + tag)); ex(a1, a2)
    link(st['then'], j['InputPin']); link(a2['then'], j['InputPin'])
    return j


X = 6900
bAll = g.branch(X, Y, 'BrStar'); link(streq(g, TK, '*', X, Y + 300, 'IsStar'), bAll['Condition']); ex(sTV, bAll)
lpS = foreach(g, gv('ItemNames', NAME_A, X + 150, Y - 300, 'S'), NAME, X + 250, Y - 500, 'StarLoop'); ex(bAll, lpS, 'then', 'Exec')
putS = put(lpS, 'LoopBody', lpS['Array Element'], X + 500, Y - 500, 'Star')
bAt = g.branch(X + 250, Y + 400, 'BrCategoryToken'); link(starts(g, TK, '@', X + 250, Y + 700, 'IsCategoryToken'), bAt['Condition']); ex(bAll, bAt, 'else')
catk = g.call(KSTR + ':RightChop', 'CategoryName', X + 450, Y + 800, count='1'); link(TK, catk['SourceString'])
lpIC = foreach(g, gv('ItemCats', STR_A, X + 450, Y + 600, 'P'), STR, X + 550, Y + 400, 'TokenCatLoop'); ex(bAt, lpIC, 'then', 'Exec')
inCat = streq(g, lower(g, lpIC['Array Element'], X + 700, Y + 750, 'ItemCatLower'), catk['ReturnValue'], X + 900, Y + 750, 'InTokenCat')
bIC = g.branch(X + 800, Y + 400, 'BrInTokenCat'); link(inCat, bIC['Condition']); ex(lpIC, bIC, 'LoopBody')
itn = item_at(g, gv('ItemNames', NAME_A, X + 800, Y + 900, 'P'), NAME, lpIC['Array Index'], X + 1000, Y + 900, 'TokenCatItem')
putC = put(bIC, 'then', itn, X + 1100, Y + 400, 'Cat')
tn = g.call(KSTR + ':Conv_StringToName', 'TokenName', X + 500, Y + 1300); link(TK, tn['InString'])
known = arrfn(g, 'Array_Find', NAME, X + 700, Y + 1300, 'FindResource', arr_pin=gv('ItemNames', NAME_A, X + 600, Y + 1450, 'K'), item_pin=tn['ReturnValue'])
kge = g.call(KML + ':GreaterEqual_IntInt', 'KnownResource', X + 900, Y + 1400, B='0'); link(known['ReturnValue'], kge['A'])
bKr = g.branch(X + 550, Y + 1100, 'BrKnownResource'); link(kge['ReturnValue'], bKr['Condition']); ex(bAt, bKr, 'else')
gameName = item_at(g, gv('ItemNames', NAME_A, X + 800, Y + 1550, 'KN'), NAME, known['ReturnValue'], X + 1000, Y + 1500, 'GameSpelling')
putR = put(bKr, 'then', gameName, X + 1100, Y + 1100, 'Res')
lU = log(g, X + 900, Y + 1800, msg_pin=concat(g, X + 900, Y + 1950, 'ProductionLimits:   not in the window: ', TK), name='LogUnknownToken'); ex(bKr, lU, 'else')

# ---- send: HudAction on a category widget (same path as a row click); no category -> ReceiveHudAction on the window
X, Y = 9500, 3000
lPs = log(g, X, Y, msg_pin=concat(g, X, Y + 150, 'ProductionLimits: profile ', item_at(g, gv('ProfileNames', STR_A, X - 300, Y + 200, 'LN'), STR, gv('Sel', INT, X - 300, Y + 300, 'LN'), X - 150, Y + 200, 'ProfileNameL'),
                                  ' = ', gv('Value', STR, X - 150, Y + 350, 'LV'), ' -> ', istr(g, arrfn(g, 'Array_Length', NAME, X - 300, Y + 450, 'WantCount', arr_pin=gv('WantNames', NAME_A, X - 400, Y + 500, 'LC'))['ReturnValue'], X - 150, Y + 450, 'WantCountStr'),
                                  ' resources, unlocked=', bstr(g, gv('Unlocked', BOOL, X - 300, Y + 600, 'LP'), X - 150, Y + 600, 'UnlockedStrP')), name='LogProfile')
ex(lpK, lPs, 'Completed')
sS0 = sv('Sender', WIDGET_T, X + 300, Y, value=None, tag='Reset'); ex(lPs, sS0)
fdC = descendants(g, gv('Win', UWT, X + 400, Y + 300, 'C'), [AWB], X + 550, Y + 200, 'WindowCategories')
ex(sS0, fdC)
sCa = sv('Arcos', ARR(WIDGET_T), X + 800, Y, fdC['ReturnValue'], tag='Send'); ex(fdC, sCa)
lpC = foreach(g, gv('Arcos', ARR(WIDGET_T), X + 850, Y + 200, 'S'), WIDGET_T, X + 950, Y, 'CategoryFindLoop'); ex(sCa, lpC, 'then', 'Exec')
notWin = g.call(KML + ':NotEqual_ObjectObject', 'NotTheWindow', X + 1100, Y + 300); link(lpC['Array Element'], notWin['A']); link(gv('Win', UWT, X + 950, Y + 400, 'NW'), notWin['B'])
noS = notb(g, is_valid(g, gv('Sender', WIDGET_T, X + 1000, Y + 550, 'NS'), X + 1100, Y + 550, 'SenderSet'), X + 1250, Y + 550, 'NoSenderYet')
bC = g.branch(X + 1200, Y, 'BrCategoryWidget'); link(andb(g, notWin['ReturnValue'], noS, X + 1350, Y + 400, 'TakeIt'), bC['Condition']); ex(lpC, bC, 'LoopBody')
sS1 = sv('Sender', WIDGET_T, X + 1450, Y, lpC['Array Element'], tag='Found'); ex(bC, sS1)
s_0 = sv('Changed', INT, X + 1300, Y - 400, value='0', tag='Reset'); ex(lpC, s_0, 'Completed')
lpWt = foreach(g, gv('WantNames', NAME_A, X + 1500, Y - 200, 'W'), NAME, X + 1600, Y - 400, 'SendLoop'); ex(s_0, lpWt, 'then', 'Exec')
WN = lpWt['Array Element']
WV = item_at(g, gv('WantVals', STR_A, X + 1600, Y + 100, 'W'), STR, lpWt['Array Index'], X + 1800, Y + 100, 'WantVal')
offv = orb(g, orb(g, streq(g, WV, 'off', X + 1900, Y + 200, 'IsOff'), streq(g, WV, '-', X + 1900, Y + 300, 'IsDash'), X + 2100, Y + 250, 'OffOrDash'),
           orb(g, orb(g, streq(g, WV, '--', X + 1900, Y + 400, 'IsDashes'), streq(g, WV, 'none', X + 1900, Y + 500, 'IsNone'), X + 2100, Y + 450, 'DashesOrNone'),
               g.call(KSTR + ':IsEmpty', 'ValEmpty', X + 1900, Y + 600)['ReturnValue'], X + 2250, Y + 500, 'OrEmpty'), X + 2400, Y + 350, 'IsOffValue')
link(WV, [n for n in g.nodes if n.name == 'ValEmpty'][0]['InString'])
num = g.call(KSTR + ':IsNumeric', 'IsNumber', X + 1900, Y + 800); link(WV, num['SourceString'])
ival = g.call(KSTR + ':Conv_StringToInt', 'ValueInt', X + 1900, Y + 950); link(WV, ival['InString'])
# skip a set whose value is already the current limit (Limits from the window read, same index as ItemNames)
cidx = arrfn(g, 'Array_Find', NAME, X + 1900, Y + 1100, 'CurrentIdx', arr_pin=gv('ItemNames', NAME_A, X + 1800, Y + 1250, 'CI'), item_pin=WN)
nlim = arrfn(g, 'Array_Length', INT, X + 1900, Y + 1300, 'LimitCount', arr_pin=gv('Limits', INT_A, X + 1800, Y + 1400, 'CI'))
inL = andb(g, g.call(KML + ':GreaterEqual_IntInt', 'IdxOk', X + 2100, Y + 1100, B='0')['ReturnValue'],
           g.call(KML + ':Less_IntInt', 'IdxInLimits', X + 2100, Y + 1250)['ReturnValue'], X + 2300, Y + 1150, 'HaveCurrent')
link(cidx['ReturnValue'], [n for n in g.nodes if n.name == 'IdxOk'][0]['A'])
il = [n for n in g.nodes if n.name == 'IdxInLimits'][0]; link(cidx['ReturnValue'], il['A']); link(nlim['ReturnValue'], il['B'])
curv = item_at(g, gv('Limits', INT_A, X + 2100, Y + 1450, 'CV'), INT, cidx['ReturnValue'], X + 2300, Y + 1400, 'CurrentLimit')
eqv = g.call(KML + ':EqualEqual_IntInt', 'SameLimit', X + 2500, Y + 1300); link(curv, eqv['A']); link(ival['ReturnValue'], eqv['B'])
unchanged = andb(g, inL, eqv['ReturnValue'], X + 2700, Y + 1250, 'Unchanged')
sAct = g.call(KML + ':SelectString', 'ActionName', X + 2600, Y + 200, A=CLEAR_ACTION, B=SET_ACTION); link(offv, sAct['bPickA'])
valid = orb(g, offv, andb(g, num['ReturnValue'], notb(g, unchanged, X + 2850, Y + 1250, 'Changes'), X + 2950, Y + 900, 'NumberChanges'), X + 3100, Y + 600, 'WillSend')
bSend = g.branch(X + 2000, Y - 400, 'BrWillSend'); link(valid, bSend['Condition']); ex(lpWt, bSend, 'LoopBody')
mk = struct_node(g, 'Make', HUDA, ['action', 'paramString', 'paramName', 'paramInt'], X + 2900, Y - 100, 'MakeLimitAction')
link(sAct['ReturnValue'], mk['action']); link(nstr(g, WN, X + 2700, Y + 50, 'WantStr'), mk['paramString']); link(WN, mk['paramName']); link(ival['ReturnValue'], mk['paramInt'])
sOK = is_valid(g, gv('Sender', WIDGET_T, X + 2300, Y - 200, 'SV'), X + 2450, Y - 200, 'HaveSender')
bSn = g.branch(X + 2300, Y - 400, 'BrHaveSender'); link(sOK, bSn['Condition']); ex(bSend, bSn)
caSn = g.cast(AWB, False, X + 2550, Y - 600, name='SenderAsArco'); link(gv('Sender', WIDGET_T, X + 2400, Y - 450, 'SC'), caSn['Object']); ex(bSn, caSn)
ha = g.call(AWB + ':HudAction', 'SendViaCategory', X + 2800, Y - 600); link(caSn['AsArcoWidgetBase'], ha['self']); link(mk['HudAction'], ha['action']); ex(caSn, ha)
caW = g.cast(AWB, False, X + 2550, Y - 300, name='WinAsArcoSend'); link(gv('Win', UWT, X + 2400, Y - 150, 'WS'), caW['Object']); ex(bSn, caW, 'else'); ex(caSn, caW, 'CastFailed')
rh = g.call(AWB + ':ReceiveHudAction', 'SendToWindow', X + 2800, Y - 300); link(caW['AsArcoWidgetBase'], rh['self']); link(mk['HudAction'], rh['action']); ex(caW, rh)
sj = knot(g, X + 3100, Y - 450, 'Sent'); link(ha['then'], sj['InputPin']); link(rh['then'], sj['InputPin'])
inc = g.call(KML + ':Add_IntInt', 'ChangedPlus1', X + 3150, Y - 250, B='1'); link(gv('Changed', INT, X + 3050, Y - 150, 'I'), inc['A'])
sc_ = sv('Changed', INT, X + 3250, Y - 450, inc['ReturnValue'], tag='Inc'); link(sj['OutputPin'], sc_['execute'])
l1 = log(g, X + 3550, Y - 450, msg_pin=concat(g, X + 3500, Y - 250, 'ProductionLimits:   ', sAct['ReturnValue'], ' ', nstr(g, WN, X + 3350, Y - 150, 'WantStrL'), ' ', WV,
                                              ' via ', bstr(g, sOK, X + 3350, Y - 50, 'ViaCategoryStr')), name='LogSend')
ex(sc_, l1)
lBad = log(g, X + 2300, Y + 1700, msg_pin=concat(g, X + 2300, Y + 1850, 'ProductionLimits:   skipped ', nstr(g, WN, X + 2100, Y + 1900, 'SkipName'), ' = ', WV, ' (same as now, or not a number)'), name='LogSkip')
ex(bSend, lBad, 'else')
lDn = log(g, X + 2000, Y - 900, msg_pin=concat(g, X + 2000, Y - 750, 'ProductionLimits: done, sent ', istr(g, gv('Changed', INT, X + 1800, Y - 700, 'D'), X + 1900, Y - 700, 'ChangedStr'),
                                              ' actions, via category widget=', bstr(g, is_valid(g, gv('Sender', WIDGET_T, X + 1700, Y - 600, 'D'), X + 1800, Y - 600, 'SenderValidD'), X + 1900, Y - 600, 'ViaStr')), name='LogDone')
ex(lpWt, lDn, 'Completed')

write('BP_MapLoad', g)

# =========================================================================== variables list + validation
VARS = {
    'BP_MapLoad': [
        ('Debug', 'Boolean'), ('Ready', 'Boolean'), ('SetupTries', 'Integer'), ('HudBound', 'Boolean'), ('Unlocked', 'Boolean'),
        ('Sel', 'Integer'), ('Cur', 'Integer'), ('Idx', 'Integer'), ('Changed', 'Integer'), ('LastX', 'Float'),
        ('Value', 'String'), ('TokKey', 'String'), ('TokVal', 'String'),
        ('Waiter', 'WBP_LimitWaiter (Object Reference)'), ('Panel', 'WBP_LimitPanel (Object Reference)'),
        ('Helper', 'WBP_LimitHelper (Object Reference)'),
        ('Win', 'User Widget (Object Reference)'), ('Injected', 'User Widget (Object Reference)'), ('Sender', 'Widget (Object Reference)'),
        ('Lines', 'String **array**'), ('PNames', 'String **array**'), ('PKeys', 'String **array**'), ('PItems', 'String **array**'),
        ('ProfileNames', 'String **array**'), ('ProfileItems', 'String **array**'), ('Tokens', 'String **array**'),
        ('ItemNames', 'Name **array**'), ('ItemCats', 'String **array**'), ('Limits', 'Integer **array**'),
        ('WantNames', 'Name **array**'), ('WantVals', 'String **array**'),
        ('ProfileButtons', 'WBP_LimitButton (Object Reference) **array**'), ('Arcos', 'Widget (Object Reference) **array**'),
        ('CatIds', 'String **array**'), ('CatNames', 'Name **array**'), ('CatItemCats', 'String **array**'),
    ],
    'WBP_LimitHelper': [('Hud', 'Production Control State UI (structure)'), ('Keys', 'Name **array**'), ('SlotKeys', 'Name **array**'),
                        ('ItemNames', 'Name **array**'), ('ItemCats', 'String **array**'), ('Limits', 'Integer **array**'), ('Unlocked', 'Boolean')],
    'WBP_LimitWaiter': [('Waited', 'Float'), ('Stage', 'Integer'), ('Done', 'Event Dispatcher (no inputs)')],
}
with open(os.path.join(OUT, 'variables.txt'), 'w') as f:
    for k, vs in VARS.items():
        f.write('## %s\n' % k)
        for n_, t_ in vs: f.write('%s\t%s\n' % (n_, t_))

import re as _re
for gname in ('BP_Startup', 'WBP_LimitHelper', 'WBP_LimitWaiter', 'BP_MapLoad'):
    p = os.path.join(OUT, gname + '.txt')
    n, bad, unl = validate(p)
    txt = open(p, encoding='utf-8').read()
    used = set(_re.findall(r'VariableReference=\(MemberName="([^"]+)",bSelfContext=True\)', txt))
    declared = set(v for v, _ in VARS.get(gname, []))
    missing = sorted(used - declared)
    logs = txt.count('MemberName="LogMessage"')
    print('%-16s %4d nodes  %s  unlinked-exec=%s  undeclared-vars=%s  unused-vars=%s  logs=%d' % (
        gname, n, 'BAD LINKS %s' % bad[:5] if bad else 'links ok', unl[:8], missing, sorted(declared - used - {'Done'}), logs))

# =========================================================================== docs/ProductionLimits-defaults.txt
HEAD = """; Production Limit Profiles - built-in profiles, every resource id, and how to write your own
;
; ---------------------------------------------------------------------------------------------------
; WHERE
;   %localappdata%\\Whiskerwood\\Saved\\mods\\ProductionLimitsConfig\\ProductionLimits.txt
;   - make the ProductionLimitsConfig folder yourself (a separate folder, so mod updates never touch it)
;   - the name must end in .txt, not .txt.txt (Windows hides extensions by default)
;   - read when you load a save or start a new game; after editing, load your save again
;
; ---------------------------------------------------------------------------------------------------
; A PROFILE = one button in the list beside the Production Limits window
;
;   [Farm only]          <- a line in [brackets] starts a profile; the text is the button label
;   * = off              <- then one  what = limit  per line
;   wheat = 200
;   @rawFood = 2500
;
; WHAT (left of =)
;   wood, planks, ...    one resource (ids listed below; they are not always the window names)
;   @rawFood, @ore, ...  every resource in that window category (list below)
;   *                    every resource in the window
;
; LIMIT (right of =)
;   a number             production pauses while storage holds more than this; 0 is allowed
;   off                  no limit, like the window's reset button (also: -  --  none  or nothing)
;   anything else is skipped
;
; RULES
;   - Clicking a profile changes only the resources it lists. Everything else keeps its current limit.
;     Start a profile with  * = off  to make it a complete setup (the built-in ones do).
;   - Lines apply top to bottom and a later line wins:  * = off  then  wood = 50
;     clears every limit except Logs;  @ore = 100  then  goldore = off  limits all ores but gold.
;   - Resources the window doesn't list (not unlocked yet, or a typo) are skipped.
;   - Upper/lower case and spaces don't matter.  ; or # starts a comment, also at the end of a line.
;     Empty lines are fine. Lines before the first [profile] are ignored.
;
; ---------------------------------------------------------------------------------------------------
; CHANGING THE BUILT-IN PROFILES  (Initial, Midgame, Advanced, No limits - listed at the end of this file)
;   Your file is read after them, top to bottom:
;   - REPLACE one:  a [profile] with the same name, e.g. [Midgame], then your lines. Your version
;                   replaces it completely (nothing of the built-in one is kept) and keeps its place.
;                   Tip: copy the built-in block from the end of this file and edit it.
;   - REMOVE one:   the name with no lines under it, e.g. just  [Advanced]
;   - RENAME one:   remove it, and add your own profile under the new name
;   - ADD new ones: any other name; new buttons come after the built-in ones, in your file's order
;   - The same name twice in your file: the later one wins.
;
; Example ProductionLimits.txt:
;
;   [Initial]            ; replace the built-in Initial with my own
;   * = off
;   berries = 2500
;   planks = 300
;
;   [Advanced]           ; remove the Advanced button
;
;   [Farm only]          ; a new button, after No limits
;   wheat = 200
;   flax = 50
;
; ---------------------------------------------------------------------------------------------------
; TIPS
;   - Copy your current limits: put any text in  ProductionLimitsConfig\\debug.txt , load your save and
;     open the Production Limits window.  Saved\\Logs\\modlog.txt  then lists every resource as
;     id = limit  (after a date and the mod name; resources without a limit may show a number,
;     write  off  for those). Delete debug.txt again when done.
;   - Production limits need an assigned administrator; without one the game ignores changes.
;   - The list can be hidden under Settings > Mods (Production Limit Profiles - profile list).
;
"""
with open(os.path.join(OUT, 'ProductionLimits-defaults.txt'), 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(HEAD)
    f.write(open(os.path.join(os.path.dirname(__file__), 'res_table.txt'), encoding='utf-8').read())
    for n_, items_ in DEFAULT_PROFILES:
        f.write('[%s]\n' % n_)
        for k_, v_ in items_: f.write('%s = %s\n' % (k_, v_))
        f.write('\n')
