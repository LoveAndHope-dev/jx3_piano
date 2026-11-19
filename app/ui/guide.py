"""使用向导：集中说明界面各区域与快捷键。"""

from app.common import *  # noqa: F401,F403


def build_guide_html() -> str:
    return """
    <h1>剑网三自动演奏工具 · 使用向导</h1>
    <p>下面按界面区域说明每个功能的用途。窗口可滚动，随时点「关闭」返回。</p>

    <h2>🎛️ 控制面板</h2>
    <ul>
      <li><b>简单模式</b>：切换到懒人模式，隐藏铺面编辑并支持一键优化播放。</li>
      <li><b>亮色 / 深色</b>：切换整套界面主题，本次运行内有效。</li>
      <li><b>置顶</b>：让主窗口保持在其他窗口之上。</li>
      <li><b>向导</b>：打开本说明。</li>
      <li><b>导入 MIDI</b>：一次可选择多个文件，导入后加入播放列表。</li>
      <li><b>新建</b>：创建一个空白曲目并立即打开铺面。</li>
      <li><b>刷新</b>：重新读取曲目并刷新列表。</li>
    </ul>

    <h2>🎻 乐器与移调</h2>
    <ul>
      <li>朝晖琴、南音三弦等拨奏类乐器的移调建议在 <b>+5 到 -5</b> 之间。</li>
    </ul>

    <h2>🧩 简单模式</h2>
    <ul>
      <li>进入后「铺面编辑」隐藏，只保留选曲与播放。</li>
      <li>演奏最低/最高键位固定为 <b>Z / 7</b>，钢琴音域固定为 <b>C2 至 B5</b>，不可调整。</li>
      <li><b>MIDI 中的所有音符需要落在 C2 至 B5 之间</b>；超出范围的音符演奏时会被跳过。</li>
      <li>「删除选中」旁的「▶️ 播放」会先整理曲谱再开始播放；再点一次切换按钮回到正常模式。</li>
    </ul>

    <h2>🎹 正常模式</h2>
    <ul>
      <li>显示「铺面编辑」，可编辑音符、调整 BPM/量化、选择映射与音域。</li>
      <li>从简单模式切回时，会重新加载未整理的原始曲目。</li>
      <li>播放使用「演奏模式」或主按钮。</li>
    </ul>

    <h3 style="margin-left: 24px;">铺面编辑工具栏</h3>
    <ul style="margin-left: 24px;">
      <li><b>第一行</b>：右侧「演奏模式 / 编辑模式」切换。进入演奏模式会自动保存当前铺面。</li>
      <li><b>第二行左侧</b>：合并主按钮——编辑模式显示「保存」，演奏模式显示「演奏」，
          播放中显示「停止」；旁边是「曲谱优化」（把选中和弦按 1/32 拍展开成琶音）。</li>
      <li><b>第二行右侧</b>：量化吸附与 BPM。修改 BPM 会按拍位重算音符时间。</li>
      <li><b>第三行</b>：演奏最低/最高键位映射，以及黄色框体的绝对音域显示。</li>
    </ul>

    <h3 style="margin-left: 24px;">钢琴窗</h3>
    <ul style="margin-left: 24px;">
      <li>拖动音符可改音高与时间；拖左右边缘调整时长；空白处拖动框选，双击空白新建。</li>
      <li><b>Ctrl + 滚轮</b>：横向缩放时间轴；<b>Shift + 滚轮</b>：纵向缩放行高（以鼠标音高为锚点）。</li>
      <li>黄色框体表示乐器音域：框内音符为绿色，框外音符变灰；背景淡色带与框体一致。</li>
      <li>播放时辅助线横向跟随；开始播放时纵向自动把黄色框体居中。</li>
      <li>标尺可点击或拖动定位播放起点；播放中锁定。</li>
    </ul>

    <h2>🎼 播放列表</h2>
    <ul>
      <li><b>点击某一行</b>：只选中并加载该曲目，不会产生多选。</li>
      <li><b>行前复选框</b>：勾选用于批量操作；点复选框不会切换当前曲目。</li>
      <li><b>长歌名</b>：鼠标停在歌名上会缓慢向左循环滚动，移出后恢复原状。</li>
      <li><b>全选</b>：勾选当前列表中的所有曲目；<b>删除选中</b>：一次确认后删除所有勾选项，
          同时清理该曲目的编辑文件。</li>
      <li><b>搜索 / 排序</b>：按名称过滤，按名称或导入时间排序。</li>
    </ul>

    <h2>📋 操作日志</h2>
    <ul>
      <li>记录导入、保存、播放、删除与错误信息；「清空」只清除显示内容。</li>
    </ul>

    <h2>⌨️ 常用快捷键</h2>
    <ul>
      <li><b>Ctrl+Z / Ctrl+Shift+Z</b>：撤销 / 前进（最多 50 步，演奏模式与播放中禁用）。</li>
      <li><b>Ctrl+C / Ctrl+X / Ctrl+V</b>：在播放辅助线处复制、剪切、粘贴选中音符。</li>
      <li><b>Shift+↑ / Shift+↓</b>：整体上移 / 下移一个八度；方向键按量化步长移动。</li>
      <li><b>Delete / Backspace</b>：删除选中音符；<b>Ctrl+A</b>：全选音符。</li>
      <li><b>ESC</b>：停止播放。</li>
    </ul>

    <h2>💾 数据位置</h2>
    <ul>
      <li><code>midi/</code>：工作曲目；<code>midi/edited/</code>：铺面保存的编辑副本。</li>
      <li><code>play_code/</code>：演奏用的按键序列 JSON；点击演奏前会按需重建。</li>
    </ul>
    """


class GuideDialog(QDialog):
    """非模态使用向导。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用向导")
        self.resize(680, 620)

        layout = QVBoxLayout(self)
        browser = QTextBrowser(self)
        browser.setOpenExternalLinks(False)
        browser.setHtml(build_guide_html())
        layout.addWidget(browser)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
