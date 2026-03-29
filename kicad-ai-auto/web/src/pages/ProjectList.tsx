/**
 * 项目列表页面 (Task 4.6-4.7)
 */

import React, { useEffect, useState, useRef } from 'react';
import { Project } from '../types';
import { projectApi } from '../services/api';
import AIProjectDialog from '../components/AIProjectDialog';

interface ProjectListProps {
  onOpenProject?: (project: Project) => void;
}

const ProjectList: React.FC<ProjectListProps> = ({ onOpenProject }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showAIDialog, setShowAIDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const isLoadingRef = useRef(false);
  const urlParamProcessedRef = useRef(false);

  // 加载项目列表
  useEffect(() => {
    if (!isLoadingRef.current) {
      isLoadingRef.current = true;
      loadProjects();
    }
  }, []);

  // 检查URL参数，自动打开指定项目
  useEffect(() => {
    if (projects.length > 0 && !urlParamProcessedRef.current) {
      urlParamProcessedRef.current = true;
      const urlParams = new URLSearchParams(window.location.search);
      const projectName = urlParams.get('project');
      if (projectName && onOpenProject) {
        const targetProject = projects.find(p => p.name === projectName);
        if (targetProject) {
          console.log('[ProjectList] Auto-opening project from URL:', projectName);
          onOpenProject(targetProject);
        } else {
          console.log('[ProjectList] Project not found from URL:', projectName);
        }
      }
    }
  }, [projects, onOpenProject]);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const response = await projectApi.listProjects();
      // 支持两种格式: { success: true, data: [...] } 或直接 [...]
      let projectList: Project[] = [];
      if (Array.isArray(response)) {
        projectList = response;
      } else if (response.success && response.data) {
        projectList = response.data;
      }

      // 去重：根据 project.id 去重
      const uniqueProjects = projectList.filter((project, index, self) =>
        index === self.findIndex((p) => p.id === project.id)
      );

      setProjects(uniqueProjects);
    } catch (err: any) {
      // 检查是否是认证错误
      const isAuthError = err?.response?.status === 401 ||
                          err?.message?.includes('无效的认证') ||
                          err?.message?.includes('Unauthorized') ||
                          err?.message?.includes('认证');

      if (isAuthError) {
        setError('请先登录后查看项目');
      } else {
        setError('Failed to load projects');
      }
      console.error(err);
    } finally {
      setLoading(false);
      isLoadingRef.current = false;
    }
  };

  // 创建新项目
  const createProject = async () => {
    if (!newProjectName.trim()) {
      alert('Please enter a project name');
      return;
    }

    try {
      const response = await projectApi.createProject({
        name: newProjectName,
        description: 'Created from KiCad Web Editor',
      });

      console.log('Create response:', response);

      // 支持两种格式: { success: true, data: {...} } 或直接 {...}
      let newProject = null;
      const resp = response as { success?: boolean; data?: Project; id?: string };
      if (resp && typeof resp === 'object') {
        if (resp.data && resp.data.id) {
          newProject = resp.data;
        } else if (resp.id) {
          newProject = resp as unknown as Project;
        }
      }

      if (newProject) {
        setProjects([...projects, newProject as Project]);
        setNewProjectName('');
        setShowCreateForm(false);
        onOpenProject?.(newProject);
      } else {
        console.error('Invalid response:', response);
        alert('Failed to create project: invalid response');
      }
    } catch (err) {
      console.error('Failed to create project:', err);
      alert('Failed to create project');
    }
  };

  // 删除项目
  const deleteProject = async (id: string) => {
    if (!confirm('Are you sure you want to delete this project?')) return;

    try {
      await projectApi.deleteProject(id);
      setProjects(projects.filter((p) => p.id !== id));
    } catch (err) {
      console.error('Failed to delete project:', err);
      alert('Failed to delete project');
    }
  };

  // 过滤项目
  const filteredProjects = projects.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#888888' }}>
        Loading projects...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#ff4444' }}>
        {error}
        <button
          onClick={loadProjects}
          style={{
            marginTop: 16,
            padding: '8px 16px',
            backgroundColor: '#4a9eff',
            color: '#ffffff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        maxWidth: 800,
        margin: '0 auto',
        padding: 24,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <h1 style={{ color: '#ffffff', fontSize: 24, margin: 0 }}>
          Projects
        </h1>
        <input
          type="text"
          placeholder="搜索项目..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            padding: '8px 12px',
            backgroundColor: '#3d3d3d',
            border: '1px solid #4d4d4d',
            borderRadius: 4,
            color: '#ffffff',
            fontSize: 14,
            width: 200,
            marginRight: 16,
          }}
        />
        <button
          onClick={() => {
            console.log('+ New Project button clicked, setting showCreateForm to true');
            setShowCreateForm(true);
          }}
          style={{
            padding: '10px 20px',
            backgroundColor: '#4a9eff',
            color: '#ffffff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 14,
          }}
        >
          + New Project
        </button>
        <button
          onClick={() => {
            console.log('AI Create button clicked');
            setShowAIDialog(true);
          }}
          style={{
            padding: '10px 20px',
            backgroundColor: '#9b59b6',
            color: '#ffffff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 14,
            marginLeft: 8,
          }}
        >
          🤖 AI 创建
        </button>
      </div>

      {/* 创建项目表单 */}
      {showCreateForm && (
        <div
          style={{
            backgroundColor: '#2d2d2d',
            padding: 16,
            borderRadius: 8,
            marginBottom: 24,
          }}
        >
          <h3 style={{ color: '#ffffff', marginTop: 0 }}>Create New Project</h3>
          <input
            type="text"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            placeholder="Project name"
            style={{
              width: '100%',
              padding: '10px',
              marginBottom: 12,
              backgroundColor: '#3d3d3d',
              border: '1px solid #4d4d4d',
              borderRadius: 4,
              color: '#ffffff',
              fontSize: 14,
            }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={createProject}
              style={{
                padding: '8px 16px',
                backgroundColor: '#4a9eff',
                color: '#ffffff',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              Create
            </button>
            <button
              onClick={() => setShowCreateForm(false)}
              style={{
                padding: '8px 16px',
                backgroundColor: '#3d3d3d',
                color: '#cccccc',
                border: '1px solid #4d4d4d',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* 项目列表 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {filteredProjects.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: 40,
              color: '#888888',
              backgroundColor: '#2d2d2d',
              borderRadius: 8,
            }}
          >
            {searchQuery ? '没有找到匹配的项目' : 'No projects yet. Create your first project!'}
          </div>
        ) : (
          filteredProjects.map((project, index) => (
            <div
              key={project.id}
              style={{
                backgroundColor: '#2d2d2d',
                padding: 16,
                borderRadius: 8,
                display: 'flex',
                alignItems: 'center',
              }}
            >
              {/* 左侧：项目编号和版本号 */}
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  marginRight: 20,
                  minWidth: 50,
                }}
              >
                <span
                  style={{
                    color: '#4a9eff',
                    fontSize: 24,
                    fontWeight: 'bold',
                  }}
                >
                  {index + 1}
                </span>
                <span
                  style={{
                    color: '#666666',
                    fontSize: 11,
                    marginTop: 2,
                  }}
                >
                  v1.0
                </span>
              </div>

              {/* 中间：项目信息 */}
              <div style={{ flex: 1 }}>
                <h3
                  style={{
                    color: '#ffffff',
                    margin: '0 0 4px 0',
                    fontSize: 16,
                    cursor: 'pointer',
                  }}
                  onClick={() => onOpenProject?.(project)}
                >
                  {project.name}
                </h3>
                <p style={{ color: '#888888', margin: 0, fontSize: 12 }}>
                  {project.description || 'No description'}
                </p>
                <p style={{ color: '#666666', margin: '4px 0 0 0', fontSize: 11 }}>
                  Updated: {new Date(project.updatedAt).toLocaleDateString()}
                </p>
              </div>

              {/* 右侧：操作按钮 */}
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={() => onOpenProject?.(project)}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#4a9eff',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 4,
                    cursor: 'pointer',
                    fontSize: 12,
                  }}
                >
                  Open
                </button>
                <button
                  onClick={() => deleteProject(project.id)}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#ff4444',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 4,
                    cursor: 'pointer',
                    fontSize: 12,
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* AI 智能创建对话框 */}
      <AIProjectDialog
        isOpen={showAIDialog}
        onClose={() => setShowAIDialog(false)}
        onProjectCreated={(createdProject) => {
          // 将 CreatedProject 转换为 Project
          const project: Project = {
            id: createdProject.id,
            name: createdProject.name,
            description: createdProject.description,
            status: createdProject.status || 'active',
            createdAt: createdProject.createdAt || new Date().toISOString(),
            updatedAt: createdProject.updatedAt || new Date().toISOString(),
            ownerId: createdProject.ownerId || 'default',
          };
          setProjects([...projects, project]);
          onOpenProject?.(project);
        }}
      />
    </div>
  );
};

export default ProjectList;
