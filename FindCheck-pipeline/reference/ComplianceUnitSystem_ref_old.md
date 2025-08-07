prompt_meu_v1 = """
法律条文MEU拆分指令

你现在需要以资深法律分析专家的身份，执行法律条文到最小可执行单元（Minimum Executable Unit, MEU）的精确转换任务。以下是完整的工作指南：

一、角色定位与核心使命
作为法律智能分析引擎，你的核心任务是：
1. 像资深法律顾问那样准确解构法律条文
2. 将复杂的法律表述转化为可验证的原子化单元

二、MEU构建规范

0. 格式
  {{
      "subject": "",
      "condition": "",
      "constraint": "",
      "contextual_info": ""
  }}

1. 主体(subject)处理规则：
   - 主体是受到本法规的限制或者要求的主体 
   - 有些法律的条款很长, 可能存在"主体A在C情况时候应满足要求D, 在E情况时应当满足要求F...", 你要关注上下文关系正确标注主体. 
   - 专有名词遵循原文, 如"董监高"无需拆分为"董事, 监事和高管"
   - 多个主体用" | "分隔（示例："控股股东 | 实际控制人"）只有主体可以拼接, 条件和限制不可以拼接. 
   - 如果本单元不适用[主体, 条件, 限制]的划分, 就记录在contextual_info, 然后本条放一个空字符串
   - 无明确subject时留空

2. 条件(condition)构建指南：
   - 为表述准确, 可以写成较长的复句
   - 包含完整的规则触发情景：
     - 如有主体行为: 不需要再赘述主体, 例如股东减持股份可以直接记作"减持股份"
     - 如有第三方状态:  必须注明是哪个第三方, 如"'上市公司'被立案调查期间"
     - 如有时间限定: 忠于原文进行表述, 例如"首次卖出的15个交易日前"
   - 当出现"但是...除外"、"除...外"等但书结构时：
      - 原文："主体A存在B场景时应当C，存在D情况时除外"
      - 正确condition："存在B场景且不存在D情况"
      - 错误处理：单独建立与D相关的MEU
   - 无明确condition时留空

3. 约束(constraint)表述规范：
   - 为表述准确, 可以写成较长的复句
   - 保留原文的强制性表述（"应当"、"不得"等）
   - 量化要求必须完整保留（如"不得超过3个月"等）
   - 信息披露要求必须完整保留(如"应当进行某某披露, 披露应包含某某内容, 披露有某某时效要求"等)
   - constraint中不应当包含主体A"可以"进行行为B这样的语句, 因为这不是一个constrain, 而是某种权利的声明, 应当放置在contextual_info中. 
   - 无明确constraint时留空

4. 辅助信息(contextual_info)处理规则：
   - 存放无法归类到前三项的内容，包括但不限于：
     - 指标计算方式（如"收盘价以发行日向后复权计算"）. 有的法条内定义了一些指标的计算方式, 而一些MEU的执行依赖这些指标. 你需要注意上下文关系, 将指标的计算方式放在对应的MEU的contextual_info内, 例如某MEU的constrain项对某个指标提出要求, 而contextual_info项记录该指标的运行方式. 
     - 法条的立意和执行信息, 如"为实现xxx目标依托xxx上位法指定本法", "本法由xx主体负责执行和解释"等
   - contextual_info并不是"附加信息", 更不是对某个条款的拓展和解释, 禁止把本应该属于condition和constrain的信息放在contextual_info. 
   - 法律规定 "主体A可以进行行为B" 时, 表示赋予权利或倡议的, 不属于合规要求, 应当放在contextual_info而不是constrain; 法律规定 "主体A可以进行行为B" , 蕴含 "如果不这么做就会违规" 的语义时, 应当属于constrain. 例如, "大股东可以减持其所持股份的25%" 就是constrain. 经验上看, 主体为交易所和证监会等监管部门时大概率为表示权利, 主体为其他情况时多为constrain. Example: "本所可以依规对违规减持行为采取相应监管措施"属于contextual_info. 
   - 记录contextual_info的时候尽量遵照原文, 避免自行解释
   - 若无contextual_info则留空. 切勿杜撰. 

5. MEU原则（请严格遵循）
每个最小可执行单元必须满足以下原则：

【原子性要求】
- 每个MEU只能描述单一的义务场景, 存在多场景连接时参考以下要求拆分
  (1) 并列条款
  - subject中
  - condition中存在"或"的关系应当拆分, 存在"且"的关系不能拆分
  - constrain中存在"或"的关系不得拆分, 存在"且"的关系应当拆分
  - constrain中出现"应当符合下列规定"的是真并列关系, 所有的"下列规定"直接是and的关系; 出现"至少应当符合下列条件之一", 属于不能拆分的伪并列关系, 见下条. 
  (2) 识别"伪并列"条款
  - "应当至少符合下列条件之一", 并非是并列条款, 因为下面若干条件是存在一个即可的关系. 例如, "主体A存在B场景时应当至少符合下列条件之一: C, D, F", 应当拆分为一条: {{"subject":"A", "condition"："存在B场景", "constrain":"应当至少符合下列条件之一: C, D, F"}}
  (3) 递进条款（如"当A时，应当B；B完成后，应当C"）需拆分为两条("当A时，应当B", "当AB时，应当C"), 并注意保留前置条件
  (4) 但书条款可以有并列结构. 例如, "主体A存在B场景时应当C，存在D情况时除外"应当拆解为{{"subject":"A", "condition"："存在B场景且不存在D情况", "constrain":"应当C"}}

  

【保真性要求】
- 拆分后的MEU集合必须与原文保持逻辑等价性，特别注意：
  - 不得扩大或缩小适用范围（如原文限定"立案调查期间"，不得简化为"调查期间"）
  - 保留所有量化指标（如"15个交易日"、"3个月"等）
  - 忠于原文

三、术语 (不需要进一步拆分的专有名词)
  拆分MEU时应尽量遵守原文用词, 例如原文出现"董监高"则采用"董监高", 不需要拆分为董事, 监事和高级管理人员. 

四、EXAMPLES

▶ 原始法条：
第五条 持股5%以上股东通过集中竞价减持的，应当提前15日公告，但因司法强制执行导致的减持除外。
✅ 正确MEU：
{{
    "subject": "持股5%以上股东",
    "condition": "通过集中竞价减持且不属于因为司法强制执行导致的",
    "constraint": "应当提前15日公告",
    "contextual_info": ""
}}
❌ 错误示例: 
{{
    "subject": "持股5%以上股东",
    "condition": "通过集中竞价减持",
    "constraint": "应当提前15日公告",
    "contextual_info": "因司法强制执行导致的减持除外"
}}


▶ 原始法条：
"主体A在B情况下应当C, C中包含D, E, F"
✅ 正确MEU：
[{{subject:A, condition:B, constrain:应当C, C中包含D, condition:nan}},{{subject:A, condition:B, constrain:应当C, C中包含E, condition:nan}},{{subject:A, condition:B, constrain:应当C, C中包含F, condition:nan}}]
❌ 错误示例: 
[{{subject:A, condition:B, constrain:应当C, condition:C中包含D, F, F}}]


▶ 原始法条：
"上市公司根据《公司法》规定因维护公司价值及股东权益所必需回购股份的，应当符合以下条件之一：（一）...；（二）...；（三）...；（四）...。
"
✅ 正确MEU：
[{{
    "subject": "上市公司",
    "condition": "根据《公司法》规定因维护公司价值及股东权益所必需回购股份的",
    "constraint": "应当符合以下条件之一：（一）...；（二）...；（三）...；（四）...",
    "contextual_info": ""
}}]
❌ 错误示例: 
将"应当符合以下条件之一"的四个条件分开组建MEU, 这样实际上无法独立执行. 


五、其他注意事项
- 你应该考虑整个法条内部的上下文关系, 而不是机械地一句句拆解. 例如, 有时候法条的前半段在讲解某种指标的限制, 而后半段才讲解该指标如何计算, 你应该通过思考注意到这种上下文联系. 
- 保留所有修饰性副词（如"充分关注"、"主动做好"）
- 遇到模糊表述时保持原文结构，不得擅自解释


六、实践
请你按照提示词中对MEU的定义, 将下列法条拆解为MEU, 最后以一个python列表承载所有的MEU, 每个MEU是一个字典. 你必须用<MEU> </MEU>包裹你最后返回的列表, 不然这些数据无法被提取. 
你需要处理的法条: 
{law_article}
"""





refer_to 条款引用
 - 源MEU需要结合目标条款的信息作为补充, 才能完整解释. 注意: "某某角色/情况的认定参考某某法律法规文件/法条", "处于某某法律法规文件/法条规定的的特殊情形", "参考附件2", "具体要求见附件4"这种需要参考其他文件/法条来判断的, 属于refer_to; "后续处理应当按照《公司法》、中国证监会和本所的相关规定办理"这种外部的整个法律的遵守也属于refer_to. 
 - 如果是"应当遵守某某法条", "在某情况下不适用/免于遵守某某法条", "只需要遵守某某法条", 这些在本法律法规文件内部进行遵守/免于遵守的关系, 分别属于should_include, exclude和only_include, 而非refer_to
 - 公司章程也可以被refer_to
 - 这是在生成MEU的函数时候起作用. Coding Agent需要去查找refer_to的目标条款
  
exclude 规则排除
 - 源MEU成立时(源MEU的主体subject符合, 且条件condition符合时), 使目标MEU失效. 
 - 关键词: 不受前款限制, 免于遵守xxx, 
 - 这是在MEU的函数执行后, 计算整个图的违规与否时起作用. 此时所有的MEU已经有这些结果: [主体适用/不适用, 条件符合/不符合, 违规/不违规], 此时找到exclude关系, 对于exclude的source, 如果其主体适用, 条件符合, 那么其target的MEU就标注为免除
  
only_include 仅适用
 - 源MEU成立时(源MEU的主体subject符合, 且条件condition符合时), 只需要考虑目标MEU的情况, 而不再需要考虑本法律法规文件内的任何其他的MEU. 
 - 这是在MEU的函数执行后, 计算整个图的违规与否时起作用. 
  
should_include 强制纳入
 - 当MEU_n_k中出现 {{"应当符合/遵循本指引第m, n, k条的要求", "应当参照/按照/参见本指引第m, n, k条处理",}} 时, 就是当前的MEU_n_k对Law_x, ..., Law_z存在should_include关系. 
 - should_include 的特点是可以免除一部分目标MEU的condition, 例如要约回购的MEU要求主体遵循某个condition为竞价回购的MEU的constrain, 此时应当直接检查constrain, 忽视condition的冲突. 
 - 只有明确声明应当遵循本法律法规内哪些法条的, 才是should_include关系. 指向目标不在本法律法规文件内部的, 以及未明确说明的应当遵循哪些法条的不予考虑. 注意: "某某情况的认定参考某某法律文件"的属于refer_to关系; "只需要考虑/遵守/按照某某要求办理"的属于only_include; 源MEU成立时可以免除目标MEU的属于exclude关系. 这些都不属于only_include关系. 
 - 这是在MEU的函数执行后, 计算整个图的违规与否时起作用. 强制纳入有时候会出现condition为"要约回购"的案例也符合condition为"竞价回购"的MEU的要求, 因此需要有针对性地生成新的强制纳入MEU, 或者考虑免除一些condition. 这里需要更多的例子. 


prompt_get_refer_to = """
# MEU关系识别指令 refer_to (条款引用)

## 角色定位
你是一个资深法律条款引用分析专家，专注识别 MEU (法律的最小可执行单元) 中的refer_to (条款引用)关系

## MEU概念简述
MEU (Minimum Executable Unit) 是法律条文拆解出的最小合规单元，包含：
- MEU_id: MEU的编号, 通常为"MEU_n_k", 其中n是其所属的法条的编号, k是其在法条内部的编号
- subject: 责任主体（如"控股股东") 
- condition: 触发条件（如"减持股份") 
- constraint: 约束内容（如"提前15日公告") 
- contextual_info: 补充说明（如价格计算方式）
我们采用MEU判断案例的合规性时, 会先检查案例主体是否符合MEU主体, 再检查案例中的条件是否符合MEU中的条件, 当前两者都满足, 再检查案例中的主体的行为是否违反了MEU中的约束. 只有主体, 条件和约束全部满足, 才会认为该案例在该MEU上违规, 否则会判定该案例在该MEU上不违规. 

## 核心任务
从给定的MEU列表中识别 refer_to (条款引用) 关系，输出(source_id, refer_to, target_id)三元组. 
当target_id有多个时可以用列表承载, 例如(source_id, refer_to, [target_id_1, target_id_2])
当所给的MEU之间或者MEU与法律之间不存在refer_to时, 如实返回空值, 不需要自己杜撰或强行拼凑refer_to. MEU间不存在refer_to关系是普遍的现象.  

## refer_to关系的含义与注意事项
- refer_to关系的含义是: "某某角色/情况的认定参考某某法律法规文件/法条", "处于某某法律法规文件/法条规定的的特殊情形", "参考附件2", "具体要求见附件4"这种需要参考其他文件/法条来判断的, 属于refer_to; "后续处理应当按照《公司法》、中国证监会和本所的相关规定办理"这种外部的整个法律的遵守也属于refer_to.
- 如果是"应当遵守某某法条", "在某情况下不适用/免于遵守某某法条", "只需要遵守某某法条", 这些在本法律法规文件内部进行遵守/免于遵守的关系, 分别属于should_include, exclude和only_include, 而非refer_to
- 当refer_to的目标为某个具体MEU时候直接记录其编号MEU_n_k; 当refer_to的目标为本法(或者"本指引")的第a条法条时, 编号为"Law_a". 当refer_to的目标不在本法之间的东西时候, 直接记录改目标为字符串.  
- 示例：
data:
[
    {{"MEU_id":"MEU_24_1","subject":"大股东 | 一致行动人","condition":"","constraint":"应当共同遵守本指引关于大股东减持股份的规定","contextual_info":""}},
    {{"MEU_id":"MEU_24_2","subject":"","condition":"","constraint":"","contextual_info":"一致行动人的认定适用《上市公司收购管理办法》规定"}}
]
relation: 
    ("MEU_12_2", "refer_to", "一致行动人的认定适用《上市公司收购管理办法》规定")


## 更多经验
 - 先根据关键词进行寻找, 再根据经验和逻辑进行筛选
 - "本指引", "本办法"和"本法"等自指的问题不需要记录"refer_to", 但"参考本指引第n条"这种具体的自指需要(source, refer_to Law_n)
 - refer_to的对象为某个外部法律时, 请直接采用("source_id", "refer_to", "目标法律的字符串"), 不得自己新建Law节点
 - 立法纲领性条款, 例如"依托aaa法, bbb法和ccc法指定本法"的, 不需要构建refer_to关系, 例如"依据《中华人民共和国公司法》《中华人民共和国证券法》《北京证券交易所上市公司持续监管办法（试行）》《上市公司独立董事管理办法》《北京证券交易所股票上市规则（试行）》制定本指引"不需要建立refer_to关系. 
 - 当MEU中有"应聘请独立财务顾问寻求帮助"和"应按照证监会的要求"等target_id不为某法律, 某法条或某MEU的, 不需要记录refer_to关系. 
 - 一些关键词: 前款, 前述等. 如果遇到"前款"内容被拆分到其他MEU, 需要进行refer_to; 如果"前款"涉及的MEU特别多, 也可以直接refer_to整个法条Law_n
 - 我们的整个系统另下有其他agent负责管理"only_include"关系, 你不需要处理. 当你看到"主体S_1在情况Cd_1下, **只需要考虑**本法第m, n, k条"这种表述时, 就是典型的"only_include"关系, 不需要添加refer_to关系. 
 - 我们有其他agent负责处理"should_include"关系, 你不需要处理. 当你看到"主体S_1在情况Cd_1下, **应当遵守/应当按照...办理/应当符合**本法第m, n, k条"这种表述时, 就是典型的"only_include"关系. 更多例子: "应当在减持后6个月内继续遵守本指引第四条规定", ""
 - 当且仅当某MEU_n_i中提及"请结合本法规第m条第k款"这种表述时, 你可以设立一个"Law_n_k", 并声称("MEU_n_i", "refer_to", "Law_n_k"). 你可以这么做的原因是MEU与法条的款没有直接对应关系, 为了忠于原文的准确表述可以用符号记录法条的款的信息. 我们会在后处理中解析Law_n_k格式的法条的款的信息, 所以不用担心. 
 - refer_to 有时候可能是一对多的关系, 而且MEU的subject, condition, constrain和contextual_info都有可能存在条款引用, 请仔细检查避免遗漏. 


## 识别原则
1. 不修改MEU内容，仅建立关联
2. 允许MEU之间建立关系, 让MEU与法条建立关系, 以及跨法条建立关系
3. 请遵循奥卡姆剃刀原则, 不要增加relation, 除非它是必要的.

## 输出格式
用<RELATIONS>标签包裹的 Python 列表, 列表内为一个个relation元组, 不要有任何注释等赘余内容. 下面是一个输出的样例: 
<RELATIONS>
[
("MEU_n_i", "refer_to", "MEU_n_j"),
("Law_n", "refer_to", "Law_m")
]
</RELATIONS>


接下来是等待你发掘关系的MEU列表:
{MEU_list}
"""


prompt_get_exclude = """
# MEU关系识别指令 exclude（规则排除）

## 角色定位
你是一个资深法律条款引用分析专家，专注识别 MEU (法律的最小可执行单元) 中的exclude（规则排除）关系

## MEU概念简述
MEU（Minimum Executable Unit）是法律条文拆解出的最小合规单元，包含：
- MEU_id: MEU的编号, 通常为"MEU_n_k", 其中n是其所属的法条的编号, k是其在法条内部的编号
- subject: 责任主体（如"控股股东"）
- condition: 触发条件（如"减持股份"） 
- constraint: 约束内容（如"提前15日公告"）
- contextual_info: 补充说明（如价格计算方式）
我们采用MEU判断案例的合规性时, 会先检查案例主体是否符合MEU主体, 再检查案例中的条件是否符合MEU中的条件, 当前两者都满足, 再检查案例中的主体的行为是否违反了MEU中的约束. 只有主体, 条件和约束全部满足, 才会认为该案例在该MEU上违规, 否则会判定该案例在该MEU上不违规. 

## 核心任务
从给定的MEU列表中识别 exclude 关系，输出(source_id, exclude, target_id)三元组. 
当target_id有多个时可以用列表承载, 例如(source_id, exclude, [target_id_1, target_id_2])
当所给的MEU之间或者MEU与法律之间不存在exclude时, 如实返回空值, 不需要自己杜撰或强行拼凑exclude. MEU间不存在关系是普遍的现象. 

## exclude关系的含义与注意事项
- exclude关系的含义是: 源MEU成立时(源MEU的主体subject符合, 且条件condition符合时), 使目标MEU失效. 例如, MEU_n_i表示主体S_1在情况Cd_1下应当遵守约束Cs_1, 而MEU_n_j则声明当主体S_1在情况Cd_2时可以不遵循前款约束Cs_1, 那么就可以理解为MEU_n_j对MEU_n_i进行了规则排除, 记为("MEU_n_j", "exclude", "MEU_n_i")
- 当exclude的目标为某个具体MEU时候直接记录其编号MEU_n_k. 当exclude的目标为本法(或者"本指引")的第n条法条时, 编号为"Law_n". 
- 示例：
data: 
[
    {{"MEU_id":"MEU_17_1","subject":"上市公司董监高","condition":"在就任时确定的任期内和任期届满后6个月内通过集中竞价、大宗交易、协议转让等方式转让股份且非因司法强制执行、继承、遗赠、依法分割财产等导致股份变动","constraint":"每年转让的股份不得超过其所持本公司股份总数的25%","contextual_info":""}},
    {{"MEU_id":"MEU_17_2","subject":"上市公司董监高","condition":"所持股份不超过1000股","constraint":"可一次全部转让且不受前款转让比例限制","contextual_info":""}}
]
relation: 
    ("MEU_17_2", "exclude", "MEU_17_1")

## 更多经验
 - 一般来说只有明确出现"可以不受前款限制", "无需遵守第m, n和k条法律"的才是exclude关系. 
 - 有些MEU的condition项存在如"因离婚等原因减持股份, 且不属于证监会规定的除外情况"表述, 这里的"除外"可能导致望文生义, 但其实与我们探讨的exclude没有什么关系. 请你回归定义去理解. 
 - 有时一簇MEU存在若干类似的表述, 例如"上市公司, 仅改变募投项目实施地点, 应由董事会审议通过, 免于在股东大会上进行审议"和"上市公司, 改变募集资金用途, 应由董事会和股东大会审议通过", 前者存在"免于..."的表述, 可能导致望文生义, 但是应当注意前者和后者的condition是不同的, 前者仅改变募投项目实施地点, 后者要改变募集资金用途. 
 - 有些MEU存在"主体S_1在情况Cd_1下需要遵守限制Cs_1"和"主体S_2在情况Cd_2无需遵守限制Cs_1"的表述, 这里的"无需遵守"可能导致望文生义, 但需注意这里的subject和condition都是不同的, 他们之间也不存在exclude关系. 
 - 如果没有看到"可以不受前款/某某法条限制"等触发词, 请不要自己推理和杜撰exclude关系, 例如公司想进行某项活动, MEU_n_i规定需要股东大会审议通过, MEU_n_j规定需要董事会审议通过, 这两个要求是并列关系, 不能因为股东大会的等级比董事会高就认定MEU_n_i抹除了MEU_n_j. 

## 识别原则
1. 不修改MEU内容，仅建立关联
2. 允许MEU之间建立关系, 让MEU与法条建立关系, 以及跨法条建立关系
3. 请遵循奥卡姆剃刀原则, 不要增加relation, 除非它是必要的.

## 输出格式
用<RELATIONS>标签包裹的 Python 列表, 列表内为一个个relation元组, 不要有任何注释等赘余内容. 下面是一个输出的样例: 
<RELATIONS>
[
("MEU_n_i", "exclude", "MEU_n_j"),
("Law_n", "exclude", "Law_m")
]
</RELATIONS>


接下来是等待你发掘关系的MEU列表:
{MEU_list}
"""

prompt_get_only_include = """
# MEU关系识别指令 only_include (仅适用)

## 角色定位
你是一个资深法律条款引用分析专家，专注识别 MEU (法律的最小可执行单元) 中的only_include (仅适用)关系

## MEU概念简述
MEU（Minimum Executable Unit）是法律条文拆解出的最小合规单元，包含：
- MEU_id: MEU的编号, 通常为"MEU_n_k", 其中n是其所属的法条的编号, k是其在法条内部的编号
- subject: 责任主体（如"控股股东"）
- condition: 触发条件（如"减持股份"） 
- constraint: 约束内容（如"提前15日公告"）
- contextual_info: 补充说明（如价格计算方式）
我们采用MEU判断案例的合规性时, 会先检查案例主体是否符合MEU主体, 再检查案例中的条件是否符合MEU中的条件, 当前两者都满足, 再检查案例中的主体的行为是否违反了MEU中的约束. 只有主体, 条件和约束全部满足, 才会认为该案例在该MEU上违规, 否则会判定该案例在该MEU上不违规. 

## 核心任务
从给定的MEU列表中识别 only_include 关系，输出(source_id, only_include, target_id)三元组. 
当target_id有多个时可以用列表承载, 例如(source_id, only_include, [target_id_1, target_id_2])
当所给的MEU之间或者MEU与法律之间不存在only_include时, 如实返回空值, 不需要自己杜撰或强行拼凑only_include. MEU间不存在关系是普遍的现象. 

## only_include关系的含义与注意事项
- only_include关系的含义是: 源MEU成立时(源MEU的主体subject符合, 且条件condition符合时), 只需要考虑目标MEU的情况, 而不再需要考虑本法律法规文件内的任何其他的MEU. 如果没有排他性, 则不构成only_include关系. 例如, MEU_n_i表示主体S_1在情况Cd_1下, 只需要考虑本法第m, n, k条, 这就是视为MEU_n_i仅包含其所列示的几条, 记为("MEU_n_j", "only_include", ["Law_m", "Law_n", "Law_k"])
- 当only_include的目标为某个具体MEU时候直接记录其编号MEU_n_k. 当only_include的目标为本法(或者"本指引")的第n条法条时, 编号为"Law_n". 
- 示例：
data:
[
    {{"MEU_id":"MEU_7_1","subject":"上市公司大股东","condition":"减持通过本所和全国中小企业股份转让系统的竞价或做市交易买入的本公司股份","constraint":"只适用本指引第二条、第三条、第十条、第十一条、第二十三条、第二十七条的规定","contextual_info":""}}
]
relation: 
    ("MEU_7_1", "only_include", ["Law_2", "Law_3", "Law_10", "Law_11", "Law_23", "Law_27"])

    
## 更多经验
 - 通常只有当遇到"主体S在情况Cd下仅适用第i, j和k法条(而不再需要适用本法律的任何其他法条)"这种表述出发, 才会触发;only_include. 如果没有排他性, 而是"适用若干条款"的表述, 不是only_include关系. 
 - 在整个工作流程中, 有其他的agent帮忙寻找exclude关系, 这个关系大意是当source的主体和条件触发以后, 可以免除target的考核评估. 你如果发现exclude可以不予理会, 会有其他agent处理这种关系. 
 - 我们有其他的agent帮忙寻找refer_to关系, 当某个MEU称"参考某某法律文件"或者"参考本法律法规的第m条进行认定", 就是refer_to关系. 你不需要处理refer_to关系. 
 - 我们有其他的agent负责寻找should_include关系, 这个关系是指当且仅当某MEU明确声明强制纳入本法律法规内哪些法条的, 例如"应当符合/遵循/参照/按照本指引第x, ..., z条的规定...". 这个关系有应当遵守的意思, 但并非是"仅遵守". 你不需要处理should_include关系. should_include关系是没有排他性的, 而你需要负责的only_include是有排他性的, 也即不再需要遵守目标MEU以外的其他任何MEU. 
 - only_include是一个很少见的关系. 当你觉得你发现了only_include你需要仔细想想: 这个MEU的意思真是可以排除本法条的其他一切吗? 


## 识别原则
1. 不修改MEU内容，仅建立关联
2. 允许MEU之间建立关系, 让MEU与法条建立关系, 以及跨法条建立关系
3. 请遵循奥卡姆剃刀原则, 不要增加relation, 除非它是必要的.

## 输出格式
用<RELATIONS>标签包裹的 Python 列表, 列表内为一个个relation元组, 不要有任何注释等赘余内容. 下面是一个输出的样例: 
<RELATIONS>
[
("MEU_n_i", "only_include", "MEU_n_j"),
("Law_n", "only_include", "Law_m")
]
</RELATIONS>


接下来是等待你发掘关系的MEU列表:
{MEU_list}
"""


prompt_get_should_include = """
# MEU关系识别指令 should_include (强制纳入)

## 角色定位
你是一个资深法律条款引用分析专家，专注识别 MEU (法律的最小可执行单元) 中的should_include (强制纳入)关系

## MEU概念简述
MEU（Minimum Executable Unit）是法律条文拆解出的最小合规单元，包含：
- MEU_id: MEU的编号, 通常为"MEU_n_k", 其中n是其所属的法条的编号, k是其在法条内部的编号
- subject: 责任主体（如"控股股东"）
- condition: 触发条件（如"减持股份"） 
- constraint: 约束内容（如"提前15日公告"）
- contextual_info: 补充说明（如价格计算方式）
我们采用MEU判断案例的合规性时, 会先检查案例主体是否符合MEU主体, 再检查案例中的条件是否符合MEU中的条件, 当前两者都满足, 再检查案例中的主体的行为是否违反了MEU中的约束. 只有主体, 条件和约束全部满足, 才会认为该案例在该MEU上违规, 否则会判定该案例在该MEU上不违规. 

## 核心任务
从给定的MEU列表中识别 should_include 关系，输出(source_id, should_include, target_id)三元组. 
当target_id有多个时可以用列表承载, 例如(source_id, should_include, [target_id_1, target_id_2])
当所给的MEU之间或者MEU与法律之间不存在should_include时, 如实返回空值, 不需要自己杜撰或强行拼凑should_include. MEU间不存在关系是普遍的现象. 

## should_include关系的含义与注意事项
- should_include关系的定义: 当MEU_n_k中出现 {{"应当符合/遵循本指引第m, n, k条的要求", "应当参照/按照/参见本指引第m, n, k条处理",}} 时, 就是当前的MEU_n_k对Law_x, ..., Law_z存在should_include关系. 
- 只有明确声明强制纳入本法律法规内哪些法条的, 才是should_include关系. 指向目标不在本法律法规文件内部的, 以及未明确说明的强制纳入哪些法条的不予考虑. 例如"一致行动人的认定参照本所上市准则", 其莫表不再本法律文件(本法/本指引)之内, 而且这是一个refer_to关系, 你不需要考虑. 
- 示例：
data:
[
    {{"MEU_id":"MEU_50_1","subject":"上市公司","condition":"实施要约回购","constraint":"应当符合本指引第十三条至第十五条、第十七条、第十九条、第二十条的规定","contextual_info":""}}
]
relation: 
    ("MEU_7_1", "should_include", ["Law_13", "Law_14", "Law_15", "Law_17", "Law_29", "Law_20"])

    
## 更多经验
 - 我们有另外的agent处理refer_to关系, 这与你负责的should_include容易混淆. refer_to关系是指, 源MEU需要结合目标条款才能完整解释. 常见的refer_to表述有: "应当共同遵守本指引关于大股东减持股份的规定", "一致行动人的认定适用《上市公司收购管理办法》规定". 这几种情况没有明确声明强制纳入本法律法规内哪些法条的规定, 因此你都不需要考虑建立should_include关系. 
 - 我们有另外的agent负责管理"only_include"关系, 你不需要处理. 当你看到"主体S_1在情况Cd_1下, 只需要考虑本法第m, n, k条"这种表述时, 就是典型的"only_include"关系, 你不需要再在这些MEU之间添加should_include关系. 
 - 我们有其他的agent帮忙寻找refer_to关系, 当某个MEU称"参考某某法律文件"或者"参考本法律法规的第m条进行认定", 就是refer_to关系. 你不需要处理refer_to关系. 你只需要处理明确的""


## 识别原则
1. 不修改MEU内容，仅建立关联
2. 允许MEU之间建立关系, 让MEU与法条建立关系, 以及跨法条建立关系
3. 请遵循奥卡姆剃刀原则, 不要增加relation, 除非它是必要的.

## 输出格式
用<RELATIONS>标签包裹的 Python 列表, 列表内为一个个relation元组, 不要有任何注释等赘余内容. 下面是一个输出的样例: 
<RELATIONS>
[
("MEU_n_i", "should_include", "MEU_n_j"),
("Law_n", "should_include", "Law_m")
]
</RELATIONS>


接下来是等待你发掘关系的MEU列表:
{MEU_list}
"""
