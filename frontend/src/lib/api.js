import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export async function createProject(name, prompt) {
  const { data } = await axios.post(`${API}/projects`, { name, prompt });
  return data;
}

export async function listProjects() {
  const { data } = await axios.get(`${API}/projects`);
  return data;
}

export async function getProject(id) {
  const { data } = await axios.get(`${API}/projects/${id}`);
  return data;
}

export async function deleteProject(id) {
  const { data } = await axios.delete(`${API}/projects/${id}`);
  return data;
}

export async function getMessages(projectId) {
  const { data } = await axios.get(`${API}/projects/${projectId}/messages`);
  return data;
}

export async function sendChat(projectId, message) {
  const { data } = await axios.post(`${API}/projects/${projectId}/chat`, { message });
  return data;
}

export async function getPipelineStage(projectId, stage) {
  const { data } = await axios.get(`${API}/projects/${projectId}/pipeline/${stage}`);
  return data;
}
