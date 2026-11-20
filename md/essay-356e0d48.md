# 3. 无重复字符的最长子串

题目描述

给定一个字符串 `s` ，请你找出其中不含有重复字符的 **最长 子串** 的长度。

**示例 1:**

**输入:** s = "abcabcbb"
**输出:** 3 
**解释:** 因为无重复字符的最长子串是 `"abc"`，所以其长度为 3。注意 "bca" 和 "cab" 也是正确答案。

**示例 2:**

**输入:** s = "bbbbb"
**输出:** 1
**解释:** 因为无重复字符的最长子串是 `"b"`，所以其长度为 1。

**示例 3:**

**输入:** s = "pwwkew"
**输出:** 3
**解释:** 因为无重复字符的最长子串是 `"wke"`，所以其长度为 3。
请注意，你的答案必须是 **子串** 的长度，`"pwke"` 是一个子序列，不是子串。

## 第一版思路

从首字母开始用[[哈希表]]记录每个字母的出现次数 出现第二次就结束并返回字典长度

然后从1，2，i，n扫描原字符串即可

每次更新最大值

注：

>s[i:]表示从i开始的字符串

代码:

```python
class Solution(object):

    def lengthOfLongestSubstring(self, s):

        maxsize=0

        def returnstringlength(s):

            hashmap={}

            for c in s:

                if c in hashmap:

                    return len(hashmap)

                hashmap[c]=1

            return len(hashmap)

        for i in range(len(s)):

            maxsize = max(returnstringlength(s[i:]), maxsize)

        return maxsize
```


## 第二版思路


想象为一个队列 左右两指针维护左右两侧 

右指针向右移动 然后遇到现有窗口里的元素让左指针

**一格一格右移** 直到窗口中不再有重复字符

直到右指针指到队列末端 取这个过程的最大值

具体计数方式还是哈希表 

用hashmap[s[left]]判断窗口中是否有字符

注:

使用del来删除字典中的键

代码：

```python
class Solution(object):

    def lengthOfLongestSubstring(self, s):

        left=0

        right=0

        maxsize=0

        hashmap={}

        while right<len(s):

            if s[right] in hashmap:

                del hashmap[s[left]] #使用del来删除字典中的键

                left+=1

                continue

            hashmap[s[right]]=1

            right+=1

            maxsize=max(right-left,maxsize)

        return maxsize
```

## 第三版思路（索引跳跃优化）

第二版在遇到重复字符时，需要让 `left` **一格一格右移**并反复执行 `del` 来清理字典。既然已经在用[[哈希表]]了，不如直接把 value 从占位符 `1` 改成**该字符最后一次出现的索引**。

这样只要发现 `s[right]` 重复，就可以直接查表让 `left` 一步跳到 `上次出现位置 + 1`，省去中间逐个移动和删除的操作。

注：

> 更新左指针时必须写 `left = max(hashmap[s[right]] + 1, left)`。因为没有手动 `del` 过期字符，哈希表里可能残留着已经滑出当前窗口左侧的旧索引，如果不取 `max`，`left` 就会向左倒退（比如 `"tmmzuxt"` 扫描到最后一个 `t` 时）。

代码：

```python
class Solution(object):
    def lengthOfLongestSubstring(self, s):
        left = 0
        right = 0
        ans = 0
        hashmap = {}
        while right < len(s):
            if s[right] in hashmap:
                left = max(hashmap[s[right]] + 1, left)  # 上次出现的位置还在窗口里才能跳，不然 left 会向左跳
            hashmap[s[right]] = right
            ans = max(ans, right - left + 1)
            right += 1
        return ans
```

## 复杂度

* **第一版：$O(n^2)$** 每个起点都重新向后扫描一遍，存在大量重复遍历。
* **第二版：$O(n)$（最坏约 $2n$ 次操作）** `left` 和 `right` 都只会从左往右移动，每个字符最多入表和出表各一次。其中 `continue` 很巧妙，确保了 `left` 能一直收缩到窗口内不再有重复字符为止。
* **第三版：$O(n)$（严格 $n$ 次循环）** 用空间换时间（懒删除），哈希表记录最新下标，遇到重复直接通过 `max` 跳跃 `left`，省去了左指针逐步收缩和频繁 `del` 的开销，是实际工程与面试中最标准的写法。