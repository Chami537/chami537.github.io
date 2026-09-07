

> 判断元素及次数是否一致 → hash 计数
> 把相同特征的东西分组 → 特征作为 key，列表作为 value


# 题1 242. 有效的字母异位词

给定两个字符串 `s` 和 `t` ，编写一个函数来判断 `t` 是否是 `s` 的 字母异位词。

思路

用hashmap遍历字符串元素 不存在的设为1 存在的+1

另 python中可以直接用`for`来遍历字符串

```python
class Solution(object):

    def isAnagram(self, s, t):

        hashmap1={}

        hashmap2={}

        for c in s:

            if c in hashmap1:

                hashmap1[c]=hashmap1[c]+1

            else:

                hashmap1[c]=1

        for d in t:

            if d in hashmap2:

                hashmap2[d]=hashmap2[d]+1

            else:

                hashmap2[d]=1

        return hashmap1==hashmap2
```
比较两个dict是否一致

空间更省的解法 只用一个hashmap去遍历

对第二个词相减即可 如果遇到不存在的字母返回False即可 

```python
class Solution(object):

    def isAnagram(self, s, t):

        hashmap = {}

  
        for c in s:

            if c in hashmap:

                hashmap[c]=hashmap[c]+1

            else:

                hashmap[c]=1


        for d in t:

            if d in hashmap:

                hashmap[d]=hashmap[d]-1

            else:

                return False

        for value in hashmap.values():

            if value !=0:

                return False

        return True
```

记住`  for value in hashmap.values():`这样的写法

# 题2  49.字母异位词分组

给你一个字符串数组，请你将 字母异位词 组合在一起。可以按任意顺序返回结果列表。

**示例 :**

**输入:** strs = ["eat", "tea", "tan", "ate", "nat", "bat"]

**输出:** \[["bat"],["nat","tan"],["ate","eat","tea"]\]

**解释：**

- 在 strs 中没有字符串可以通过重新排列来形成 `"bat"`。
- 字符串 `"nat"` 和 `"tan"` 是字母异位词，因为它们可以重新排列以形成彼此。
- 字符串 `"ate"` ，`"eat"` 和 `"tea"` 是字母异位词，因为它们可以重新排列以形成彼此。

思路

开始的想法是对于每一个word都建立一个hash 写一个`makehash`函数 然后将makehash的结果作为新的hash进行匹配

这就引申出几个问题

- 1. makehash的返回值应该是什么？
- 2. 如何确保对于排列不同的单词makehash的返回值相同？
- 3. 得到key后如何建立起恰当的key value 对应关系

最初想用字符频次 dict 作为特征，因为上一题中我们得到的返回值就是一个dict

但是 [[列表与词典|词典]]里的key只能是不可变元素
如str int 还有不含可变元素的[[tuple]]

因此这里选择更简单的规范化方式：tuple(sorted(word))。同时解决了排序问题

于是我们得到的返回值就是

```python
tuple(sorted(words))
```

下一步就是将这个返回值作为key

自然想到 key对应的value应该是谁

题目要求的返回值是一个列表 因此 key应该和列表对应

即`group`为

```
{"key":["abc"]
}
```

类似表达

已存在的key用`append()`处理即可

不存在的建立对应关系

最后只取value部分即可 再用`list`进行转化

代码如下

```python
class Solution(object):

    def groupAnagrams(self, strs):

        groups={}

        def makehash(word):

            return tuple(sorted(word))

        for word in strs:

            key =makehash(word)

            if key in groups:

                groups[key].append(word)

            else:

                groups[key]=[word]

        return list(groups.values())
```

总结一下

>核心模式：把原始数据转换成统一的“特征 key”，再利用 hashmap 分组
