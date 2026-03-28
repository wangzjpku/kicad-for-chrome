# -*- coding: utf-8 -*-

# 修复 ProjectList.tsx 的搜索功能
project_file = 'E:/0-007-MyAIOS/projects/1-kicad-for-chrome/kicad-ai-auto/web/src/pages/ProjectList.tsx'
with open(project_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 移除错误添加的代码
old_bad = ''') : (
          // 过滤项目
  const filteredProjects = projects.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  filteredProjects.map((project) => ('''

new_good = ''') : (
          projects'''

if old_bad in content:
    content = content.replace(old_bad, new_good)
    print('Fixed bad code')

# 保存
with open(project_file, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
