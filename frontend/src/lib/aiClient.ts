/**
 * AI Client - Communication with backend AI assistant API
 * Provides chat and history retrieval functionality
 */

const API_BASE = import.meta.env.VITE_AI_API_URL || '/api/ai';

interface ChatResponse {
    reply?: string;
    message?: string;
    text?: string;
    tools_used?: string[];
    session_id?: string;
}

interface HistoryMessage {
    role: 'user' | 'assistant' | 'tool';
    content?: string;
    text?: string;
    timestamp?: string;
}

export const aiClient = {
    /**
     * Send a chat message to the AI assistant
     */
    async chat(sessionId: string, message: string): Promise<ChatResponse> {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                message,
            }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || error.error || `AI request failed: ${response.status}`);
        }

        return response.json();
    },

    /**
     * Get chat history for a session
     */
    async history(sessionId: string): Promise<HistoryMessage[]> {
        const response = await fetch(`${API_BASE}/history/${sessionId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            // Return empty array if history not found
            if (response.status === 404) {
                return [];
            }
            throw new Error(`Failed to fetch history: ${response.status}`);
        }

        const data = await response.json();
        return data.messages || data.history || [];
    },

    /**
     * Clear chat history for a session
     */
    async clearHistory(sessionId: string): Promise<void> {
        await fetch(`${API_BASE}/history/${sessionId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        });
    },
};

export default aiClient;
