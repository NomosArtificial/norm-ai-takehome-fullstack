/**
 * API service for interacting with the backend
 */

// Define the base URL for API requests
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Define interfaces for API data
export interface Citation {
  source: string;
  text: string;
}

export interface QueryResult {
  query: string;
  response: string;
  citations: Citation[];
}

/**
 * Send a query to the backend API
 * @param query The query string to send
 * @returns A promise that resolves to the query result
 */
export async function sendQuery(query: string): Promise<QueryResult> {
  try {
    const response = await fetch(`${API_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        `API error: ${response.status} ${response.statusText}${
          errorData.detail ? ` - ${errorData.detail}` : ''
        }`
      );
    }

    return await response.json();
  } catch (error) {
    console.error('Error sending query:', error);
    throw error;
  }
}

/**
 * Check the health of the API
 * @returns A promise that resolves to true if the API is healthy
 */
export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/health`);
    return response.ok;
  } catch (error) {
    console.error('API health check failed:', error);
    return false;
  }
}