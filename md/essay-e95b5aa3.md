# 栈

Python 可以直接用 `list` 实现栈。

```python
stack.append(x)  # 入栈
stack.pop()      # 出栈
stack[-1]        # 获取栈顶
```

栈的特点：**后进先出 LIFO**


# 20. 有效的括号

## 思路

遇到左括号就入栈。

遇到右括号时检查栈顶元素：

- `)` 对应 `(`
    
- `]` 对应 `[`
    
- `}` 对应 `{`
    

匹配就出栈，不匹配直接返回 `False`。

遍历结束后如果栈不为空，说明还有左括号没有匹配。

另外括号一定成对出现，所以长度为奇数可以直接返回 `False`。

## 代码

```python
class Solution(object):
    def isValid(self, s):

        stack = []

        if len(s) % 2 != 0:
            return False

        for c in s:

            if c == "[" or c == "{" or c == "(":
                stack.append(c)

            if c == "]":
                if not stack or stack[-1] != "[":
                    return False
                stack.pop()

            if c == "}":
                if not stack or stack[-1] != "{":
                    return False
                stack.pop()

            if c == ")":
                if not stack or stack[-1] != "(":
                    return False
                stack.pop()

        return len(stack) == 0
```

## 踩到的坑

一开始遇到右括号直接访问：

```python
stack[-1]
```

如果栈为空会报错。

例如：

```text
)(
```

所以必须先判断：

```python
if not stack or stack[-1] != "(":
    return False
```

## 复杂度

时间复杂度：`O(n)`

空间复杂度：`O(n)`


# 155. 最小栈

设计一个支持 `push` ，`pop` ，`top` 操作，并能在常数时间内检索到最小元素的栈。

实现 `MinStack` 类:

- `MinStack()` 初始化堆栈对象。
- `void push(int value)` 将元素 `value` 推入堆栈。
- `void pop()` 删除堆栈顶部的元素。
- `int top()` 获取堆栈顶部的元素。
- `int getMin()` 获取堆栈中的最小元素。

## 第一版思路

普通栈的：

```text
push
pop
top
```

都可以做到 `O(1)`。

但是如果 `getMin()` 直接写：

```python
min(self.stack)
```

就需要遍历整个栈，时间复杂度为 `O(n)`。

题目要求 `getMin()` 也是 `O(1)`。

## 第二版思路

用一个栈维护最小值

```python
self.min_stack = []
```

用来记录**当前每一层对应的最小值**。

例如：

```text
stack:     [5, 2, 3, 1]
min_stack: [5, 2, 2, 1]
```

这样：

```python
self.min_stack[-1]
```

永远就是当前最小值。

每次入栈时：

```python
min(value, self.min_stack[-1])
```

得到新的最小值并存入 `min_stack`。

两个栈出栈时也要同步。

## 代码

```python
class MinStack(object):

    def __init__(self):
        self.stack = []
        self.min_stack = []

    def push(self, value):
        self.stack.append(value)

        if not self.min_stack:
            self.min_stack.append(value)
        else:
            self.min_stack.append(
                min(value, self.min_stack[-1])
            )

    def pop(self):
        self.stack.pop()
        self.min_stack.pop()

    def top(self):
        return self.stack[-1]

    def getMin(self):
        return self.min_stack[-1]
```

## 踩到的坑

### 1. `list` 没有 `.top()`

错误：

```python
self.min_stack.top()
```

应该使用：

```python
self.min_stack[-1]
```

### 2. 第一次入栈时为空

不能直接：

```python
self.min_stack[-1]
```

所以第一次要单独判断：

```python
if not self.min_stack:
```

### 3. `if` 后漏写 `else`

一开始写成：

```python
if not self.min_stack:
    self.min_stack.append(value)

self.min_stack.append(min(value, self.min_stack[-1]))
```

这样第一次 `push` 会执行两次 `append`。

所以应该写：

```python
if not self.min_stack:
    self.min_stack.append(value)
else:
    self.min_stack.append(min(value, self.min_stack[-1]))
```

### 4. 两个栈要同步

`pop()` 时必须：

```python
self.stack.pop()
self.min_stack.pop()
```

否则两个栈的状态会错位。

## 时间复杂度

```text
push    O(1)
pop     O(1)
top     O(1)
getMin  O(1)
```

空间复杂度：`O(n)`

## 总结

这道题的关键来自题目的要求：

```text
getMin = O(1)
```

如果在查询的时候再使用：

```python
min(self.stack)
```

就需要重新遍历。

所以思路变成：

> 查询的时候不能算，就在数据变化的时候提前算好。

`min_stack` 保存的是**主栈每一个历史状态对应的最小值**。

例如：

```text
stack:     [5, 2, 3]
min_stack: [5, 2, 2]
```

弹出 `3`：

```text
stack:     [5, 2]
min_stack: [5, 2]
```

之前的最小值状态就自动恢复了。

这题值得记住的不是“双栈”本身，而是：

```text
需要 O(1) 查询
↓
在更新数据时提前维护答案
↓
使用额外空间保存历史状态
```

也就是 **空间换时间 + 辅助栈维护状态**。