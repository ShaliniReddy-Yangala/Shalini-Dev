import axios from 'axios';
import { path } from '../path';

const skillsService = {
  // Get detailed skills for a job
  getDetailedSkills: async (jobId) => {
    try {
      const response = await axios.get(`${path}/jobs/${jobId}/skills/detailed`);
      return response.data;
    } catch (error) {
      console.error('Error fetching detailed skills:', error);
      throw error;
    }
  },

  // Create new skills
  createSkill: async (skillData) => {
    try {
      const response = await axios.post(`${path}/jobs/create-skill/`, skillData);
      return response.data;
    } catch (error) {
      console.error('Error creating skill:', error);
      throw error;
    }
  },

  // Update existing skills
  updateSkills: async (skillId, skillData) => {
    try {
      const response = await axios.put(`${path}/jobs/skill/${skillId}`, skillData);
      return response.data;
    } catch (error) {
      console.error('Error updating skills:', error);
      throw error;
    }
  },

  // Delete skills
  deleteSkills: async (skillId) => {
    try {
      const response = await axios.delete(`${path}/jobs/skill/${skillId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting skills:', error);
      throw error;
    }
  }
};

export default skillsService; 