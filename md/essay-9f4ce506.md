# 283.移动零

题目描述

给定一个数组 `nums`，编写一个函数将所有 `0` 移动到数组的末尾，同时保持非零元素的相对顺序。

**请注意** ，必须在不复制数组的情况下原地对数组进行操作。

### 第一版思路

统计有多少个零

两两交换位置挪到末尾部分

挪n次就能挪完

代码

```python
class Solution(object):

    def moveZeroes(self, nums):

        zerocount=0

        for num in nums:

            if num==0:

                zerocount+=1

        j=0

        while j<zerocount:

            for i,num in enumerate(nums):

                if num==0 and i<len(nums)-1:

                    temp=nums[i+1]

                    nums[i+1]=nums[i]

                    #num只是enumerate取出来的一个变量 不会真正修改nums[i]

                    nums[i]=temp

            j+=1
```

然后测试用例74/75 

未通过的用例是因为timeout了

需要减小时间复杂度

### 第二版思路

考虑把所有不为零的元素重新排序 在最后空余的位置重新填上0即可

用一个指针指向当前可以放元素的位置 是0的话就跳过

最后补上即可 有x个0 假设数组长度是l 那么最后j的值为l-x 

while判断 补上剩余的0即可

代码如下

```python
class Solution(object):

    def moveZeroes(self, nums):

        j = 0

        for i in range(len(nums)):

            if nums[i]!=0:

                nums[j]=nums[i]

                j+=1

  

        while j<len(nums):

            nums[j]=0

            j+=1
```

>这题真正值得记住的东西:

一种很经典的：

```
读指针 + 写指针
```

模式。

```
i：负责读取原数组

j：负责告诉我们“下一个符合条件的元素该写在哪里”
```

可以抽象成：

```
j = 0

for i in range(len(nums)):
    if 元素符合条件:
        nums[j] = nums[i]
        j += 1
```

以后遇到：

```
删除某类元素
过滤数组
移动元素
压缩数组
保留满足条件的元素
```

都可以想到这种思路。
# 11. 盛最多水的容器

题目描述

给定一个长度为 `n` 的整数数组 `height` 。有 `n` 条垂线，第 `i` 条线的两个端点是 `(i, 0)` 和 `(i, height[i])` 。

找出其中的两条线，使得它们与 `x` 轴共同构成的容器可以容纳最多的水。

返回容器可以储存的最大水量。

![Pasted-image-20260907222843](/images/essays/双指针法/Pasted-image-20260907222843.png)

定义left right 两根柱子

面积计算则为
```python
area=min(height[left],height[right])*(right-left)
```

暴力解法自然是套两遍for比较

优化方式 先拿宽度最大的 也就是取两边的边界情况

然后向内移动height较小的那个指针即可

每移动一次更新一次最大面积

直到左右指针相遇

代码实现

```python
class Solution(object):
    def maxArea(self, height):
        left = 0
        right = len(height) - 1
        maxarea = 0

        while left < right:
            area = min(height[left], height[right]) * (right - left)
            maxarea = max(maxarea, area)

            if height[left] <= height[right]:
                left += 1
            else:
                right -= 1

        return maxarea
```

时间复杂度为

$$O(n)$$
# 双指针理解

可以这么想

>用两个位置变量维护当前问题中最重要的两个位置，并通过某种规则移动它们，从而避免暴力枚举。





# 15. 三数之和

## 题目描述

找出数组中所有满足：

`nums[i] + nums[j] + nums[k] = 0`

的不重复三元组。

---

## 最开始的想法

固定一个数 `nums[i]` 后，问题就变成：

`nums[left] + nums[right] = -nums[i]`

本质上是「两数之和」。

两数之和可以用哈希表，但这题还需要处理大量重复元素，所以：

**排序 + 双指针更自然。**

---

## 思路

先对整个数组排序。

然后枚举 `i`，固定第一个数：

```text
nums[i]
````

在它右侧设置：

```python
left = i + 1
right = len(nums) - 1
```

目标：

```python
nums[left] + nums[right] == -nums[i]
```

### 双指针移动

因为数组已经排序：

```text
两数和 < 目标
→ 和太小
→ left += 1

两数和 > 目标
→ 和太大
→ right -= 1

两数和 == 目标
→ 找到答案
```

---

## 去重

### 1. 固定数 `i` 去重

如果当前数字和上一个数字相同：

```python
if i > 0 and nums[i] == nums[i - 1]:
    continue
```

原因：

同一个数已经作为第一个数搜索过一次，再搜索只会产生重复答案。

---

### 2. left / right 去重

找到一个答案以后，要跳过相同的数字。

```python
while left < right and nums[left] == nums[left + 1]:
    left += 1

while left < right and nums[right] == nums[right - 1]:
    right -= 1
```

然后再：

```python
left += 1
right -= 1
```

`left < right` 要写在 `and` 前面，因为 Python 的 `and` 从左往右判断并且具有短路性质。

---

## 我的代码

```python
class Solution(object):
    def threeSum(self, nums):
        numssorted = sorted(nums)
        outcome = []

        for i in range(len(numssorted) - 2):

            if i >= 1 and numssorted[i] == numssorted[i - 1]:
                continue

            left = i + 1
            right = len(numssorted) - 1
            remnant = -numssorted[i]

            while left < right:

                if numssorted[left] + numssorted[right] < remnant:
                    left += 1

                elif numssorted[left] + numssorted[right] > remnant:
                    right -= 1

                else:
                    outcome.append([
                        numssorted[i],
                        numssorted[left],
                        numssorted[right]
                    ])

                    while left < right and numssorted[left] == numssorted[left + 1]:
                        left += 1

                    while left < right and numssorted[right] == numssorted[right - 1]:
                        right -= 1

                    left += 1
                    right -= 1

        return outcome
```

---

## 这题踩的坑

### `return` 不能放在 for 循环内部

否则只会搜索 `i = 0` 的情况，后面的数字不会继续枚举。

### 要用 `if / elif / else`

三个情况互斥。

如果写三个独立的 `if`，第一个判断修改指针后，后面的判断会立刻使用新的指针，逻辑容易出错。

### 去重时要注意边界

```python
while left < right and ...
```

先判断双指针是否合法，再访问数组。

---

## 复杂度

排序：

`O(n log n)`

外层枚举 + 双指针：

`O(n²)`

总时间复杂度：

`O(n²)`

额外空间复杂度取决于排序实现，不考虑排序空间时可以看作 `O(1)`。

---

## 一句话总结

**三数之和 = 排序 + 固定一个数 + 双指针做两数之和 + 三处去重。**
