# Spec Delta

## MODIFIED Requirements

### Requirement: Shift+滚轮横向缩放

缩放修饰键由 Shift 改为 Ctrl：按住 Ctrl 滚动滚轮 SHALL 横向放大或缩小时间轴（向上放大、向下缩小），缩放 MUST 以鼠标指针所在的时间点为锚点，使该时间点在缩放前后保持在同一横向屏幕位置，并受 10～600 px/s 的最小与最大比例限制。按住 Shift 滚动滚轮 MUST 恢复为普通滚动，不再改变缩放比例；其余既有要求（不按修饰键时保持原有滚动、缩放后时间语义不变）保持不变。

#### Scenario: 向上滚动放大

- **WHEN** 按住 Ctrl 把滚轮向上滚动一格
- **THEN** 时间轴放大，鼠标指针下的时间点在屏幕上保持不动，可见时间范围变短

#### Scenario: 向下滚动缩小

- **WHEN** 按住 Ctrl 把滚轮向下滚动一格
- **THEN** 时间轴缩小，鼠标指针下的时间点保持不动，可见时间范围变长

#### Scenario: 不按 Shift 时保持原有滚动

- **WHEN** 不按 Ctrl 滚动滚轮（包括按住 Shift）
- **THEN** 铺面按原有行为滚动，横向缩放比例不变
