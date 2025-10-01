# Internal Logs System - Frontend Implementation Guide

## Overview

The Internal Logs System tracks all CRUD operations across the HRMS application. This system records user actions for audit trails, debugging, and activity monitoring.

## API Endpoints

### Base URL
```
/api/internal-logs
```

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/internal-logs/` | Create a new log entry |
| GET | `/internal-logs/` | Get paginated logs with filtering |
| GET | `/internal-logs/{log_id}` | Get specific log entry |
| PUT | `/internal-logs/{log_id}` | Update log entry |
| DELETE | `/internal-logs/{log_id}` | Delete log entry |
| GET | `/internal-logs/stats/summary` | Get summary statistics |

## Data Models

### Log Entry Structure
```typescript
interface InternalLog {
  id: number;
  page: string;                    // Required: Page where action occurred
  sub_page?: string;               // Optional: Sub-page or section
  action: string;                  // Required: Description of the action
  action_type: "Create" | "Update" | "Delete";  // Required: Type of operation
  timestamp: string;               // Auto-generated: ISO datetime
  performed_by: string;            // Required: User who performed the action
  description?: string;            // Optional: Additional details
  created_at: string;              // Auto-generated
  updated_at?: string;             // Auto-generated
}
```

### Create Log Request
```typescript
interface CreateLogRequest {
  page: string;
  sub_page?: string;
  action: string;
  action_type: "Create" | "Update" | "Delete";
  performed_by: string;
  description?: string;
}
```

### Filter Parameters
```typescript
interface LogFilters {
  page?: number;                   // Page number (default: 1)
  items_per_page?: number;         // Items per page (1-100, default: 50)
  search?: string;                 // Search across all text fields
  page_filter?: string;            // Filter by specific page
  action_type_filter?: string;     // Filter by action type
  performed_by_filter?: string;    // Filter by user
  start_date?: string;             // Start date (ISO format)
  end_date?: string;               // End date (ISO format)
  sort_key?: string;               // Sort field (timestamp, page, action, etc.)
  sort_order?: "asc" | "desc";    // Sort order (default: desc)
}
```

## Implementation Examples

### 1. Creating a Log Entry

```typescript
// Example: Logging a candidate status update
const logCandidateUpdate = async (candidateId: string, oldStatus: string, newStatus: string, user: string) => {
  try {
    const logData: CreateLogRequest = {
      page: "Candidates",
      sub_page: "Candidate Details",
      action: `Updated candidate ${candidateId} status from "${oldStatus}" to "${newStatus}"`,
      action_type: "Update",
      performed_by: user,
      description: `Status change for candidate ${candidateId}`
    };

    const response = await fetch('/api/internal-logs/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Include your authentication headers
      },
      body: JSON.stringify(logData)
    });

    if (!response.ok) {
      throw new Error('Failed to create log entry');
    }

    return await response.json();
  } catch (error) {
    console.error('Error creating log entry:', error);
    // Handle error appropriately
  }
};
```

### 2. Retrieving Logs with Filtering

```typescript
// Example: Getting logs with filters
const getLogs = async (filters: LogFilters = {}) => {
  try {
    const params = new URLSearchParams();
    
    // Add filter parameters
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.items_per_page) params.append('items_per_page', filters.items_per_page.toString());
    if (filters.search) params.append('search', filters.search);
    if (filters.page_filter) params.append('page_filter', filters.page_filter);
    if (filters.action_type_filter) params.append('action_type_filter', filters.action_type_filter);
    if (filters.performed_by_filter) params.append('performed_by_filter', filters.performed_by_filter);
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.sort_key) params.append('sort_key', filters.sort_key);
    if (filters.sort_order) params.append('sort_order', filters.sort_order);

    const response = await fetch(`/api/internal-logs/?${params.toString()}`, {
      method: 'GET',
      headers: {
        // Include your authentication headers
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch logs');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching logs:', error);
    throw error;
  }
};

// Usage examples:
// Get all logs
const allLogs = await getLogs();

// Get logs for specific page
const candidateLogs = await getLogs({ page_filter: "Candidates" });

// Get recent updates
const recentUpdates = await getLogs({ 
  action_type_filter: "Update",
  start_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
});

// Search for specific actions
const searchResults = await getLogs({ search: "status update" });
```

### 3. Getting Summary Statistics

```typescript
const getLogStats = async () => {
  try {
    const response = await fetch('/api/internal-logs/stats/summary', {
      method: 'GET',
      headers: {
        // Include your authentication headers
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch log statistics');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching log statistics:', error);
    throw error;
  }
};
```

## Common Use Cases

### 1. Job Management
```typescript
// Log job creation
await logAction({
  page: "Jobs",
  sub_page: "Job Creation",
  action: `Created new job: ${jobTitle}`,
  action_type: "Create",
  performed_by: currentUser,
  description: `Job ID: ${jobId}, Department: ${department}`
});

// Log job status change
await logAction({
  page: "Jobs",
  sub_page: "Job Management",
  action: `Updated job status from "${oldStatus}" to "${newStatus}"`,
  action_type: "Update",
  performed_by: currentUser,
  description: `Job ID: ${jobId}`
});
```

### 2. Candidate Management
```typescript
// Log candidate creation
await logAction({
  page: "Candidates",
  sub_page: "Candidate Registration",
  action: `Added new candidate: ${candidateName}`,
  action_type: "Create",
  performed_by: currentUser,
  description: `Email: ${email}, Job: ${jobTitle}`
});

// Log interview scheduling
await logAction({
  page: "Candidates",
  sub_page: "Interview Management",
  action: `Scheduled ${interviewRound} interview for ${candidateName}`,
  action_type: "Update",
  performed_by: currentUser,
  description: `Interview Date: ${interviewDate}, Interviewer: ${interviewer}`
});
```

### 3. User Management
```typescript
// Log role assignment
await logAction({
  page: "User Management",
  sub_page: "Role Assignment",
  action: `Assigned role "${roleName}" to user ${userEmail}`,
  action_type: "Update",
  performed_by: currentUser,
  description: `Role Template: ${roleTemplate}, Expiry: ${expiryDate}`
});
```

## Utility Functions

### Generic Logging Function
```typescript
const logAction = async (logData: CreateLogRequest) => {
  try {
    const response = await fetch('/api/internal-logs/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Include your authentication headers
      },
      body: JSON.stringify(logData)
    });

    if (!response.ok) {
      console.warn('Failed to log action:', logData);
    }
  } catch (error) {
    console.error('Error logging action:', error);
    // Don't throw error to avoid breaking main functionality
  }
};
```

### React Hook for Logging
```typescript
import { useCallback } from 'react';

export const useLogging = () => {
  const logAction = useCallback(async (logData: CreateLogRequest) => {
    try {
      const response = await fetch('/api/internal-logs/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Include your authentication headers
        },
        body: JSON.stringify(logData)
      });

      if (!response.ok) {
        console.warn('Failed to log action:', logData);
      }
    } catch (error) {
      console.error('Error logging action:', error);
    }
  }, []);

  return { logAction };
};
```

## Error Handling

### Best Practices
1. **Non-blocking**: Logging should not block main functionality
2. **Graceful degradation**: If logging fails, continue with the operation
3. **User feedback**: Don't show logging errors to end users
4. **Retry logic**: Consider implementing retry for failed log entries

```typescript
const safeLogAction = async (logData: CreateLogRequest, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      await logAction(logData);
      return; // Success
    } catch (error) {
      if (i === retries - 1) {
        console.error('Failed to log action after retries:', error);
      } else {
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1))); // Exponential backoff
      }
    }
  }
};
```

## Integration Points

### 1. Form Submissions
```typescript
const handleFormSubmit = async (formData: any) => {
  try {
    // Submit form data
    const response = await submitForm(formData);
    
    // Log the action
    await logAction({
      page: "Candidates",
      sub_page: "Candidate Form",
      action: "Created new candidate",
      action_type: "Create",
      performed_by: currentUser,
      description: `Candidate: ${formData.name}, Email: ${formData.email}`
    });

    // Show success message
    showSuccessMessage("Candidate created successfully!");
  } catch (error) {
    // Handle error
  }
};
```

### 2. Status Changes
```typescript
const handleStatusChange = async (itemId: string, oldStatus: string, newStatus: string) => {
  try {
    // Update status in backend
    await updateStatus(itemId, newStatus);
    
    // Log the status change
    await logAction({
      page: "Candidates",
      sub_page: "Status Management",
      action: `Changed status from "${oldStatus}" to "${newStatus}"`,
      action_type: "Update",
      performed_by: currentUser,
      description: `Item ID: ${itemId}`
    });
  } catch (error) {
    // Handle error
  }
};
```

### 3. Delete Operations
```typescript
const handleDelete = async (itemId: string, itemName: string) => {
  try {
    // Confirm deletion
    const confirmed = await confirmDelete(itemName);
    if (!confirmed) return;
    
    // Delete item
    await deleteItem(itemId);
    
    // Log the deletion
    await logAction({
      page: "Jobs",
      sub_page: "Job Management",
      action: `Deleted job: ${itemName}`,
      action_type: "Delete",
      performed_by: currentUser,
      description: `Job ID: ${itemId}`
    });
  } catch (error) {
    // Handle error
  }
};
```

## Testing

### Mock Implementation for Testing
```typescript
// Mock for testing environments
const mockLogAction = async (logData: CreateLogRequest) => {
  console.log('Mock log entry:', logData);
  return Promise.resolve();
};

// Use in development/testing
const logAction = process.env.NODE_ENV === 'production' 
  ? realLogAction 
  : mockLogAction;
```

## Security Considerations

1. **Authentication**: Ensure all requests include proper authentication headers
2. **Authorization**: Verify user permissions before logging sensitive actions
3. **Data Sanitization**: Sanitize user input before logging
4. **PII Protection**: Avoid logging sensitive personal information

## Performance Considerations

1. **Async Logging**: Always log asynchronously to avoid blocking UI
2. **Batch Logging**: Consider batching multiple log entries for better performance
3. **Error Boundaries**: Implement error boundaries to prevent logging errors from crashing the app
4. **Rate Limiting**: Implement rate limiting for log creation to prevent abuse

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure the API endpoint is properly configured for CORS
2. **Authentication Errors**: Verify authentication headers are included
3. **Network Errors**: Implement proper error handling and retry logic
4. **Validation Errors**: Ensure all required fields are provided

### Debug Mode
```typescript
const DEBUG_LOGGING = process.env.NODE_ENV === 'development';

const logAction = async (logData: CreateLogRequest) => {
  if (DEBUG_LOGGING) {
    console.log('Logging action:', logData);
  }
  
  // ... rest of implementation
};
```

## Support

For questions or issues related to the internal logs system:
- Check the API documentation
- Review the backend logs for errors
- Contact the backend team for technical support


