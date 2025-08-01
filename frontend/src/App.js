import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (message = inputValue) => {
    if (!message.trim() || isLoading) return;

    const userMessage = {
      type: 'user',
      content: message,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError('');

    try {
      const response = await axios.post('/api/v1/chat/', {
        message: message,
        property_id: 'demo_property',
        date_range: 'last_30_days'
      });

      const assistantMessage = {
        type: 'assistant',
        content: response.data.response,
        confidence: response.data.confidence,
        queryType: response.data.query_type,
        executionTime: response.data.execution_time,
        timestamp: new Date().toLocaleTimeString(),
        data: response.data.data
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      if (response.data.suggestions) {
        setSuggestions(response.data.suggestions);
      }

    } catch (err) {
      setError('抱歉，發生了錯誤。請稍後再試。');
      console.error('Chat error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage();
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion);
    setSuggestions([]);
  };

  return (
    <div className="app">
      <header className="header">
        <h1>GA+</h1>
        <p>Google Analytics 4 對話式AI分析平台</p>
      </header>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="loading">
              歡迎使用 GA+！請輸入您的 GA4 分析問題，例如：
              <br />
              • "昨天有多少訪客？"
              <br />
              • "最熱門的頁面是什麼？" 
              <br />
              • "主要流量來源有哪些？"
            </div>
          )}
          
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.type}`}>
              <div className="message-content">
                {message.content}
              </div>
              <div className="message-meta">
                {message.timestamp}
                {message.confidence && (
                  <span> • 信心度: {(message.confidence * 100).toFixed(1)}%</span>
                )}
                {message.executionTime && (
                  <span> • 執行時間: {message.executionTime.toFixed(2)}s</span>
                )}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="message assistant">
              <div className="loading">正在分析您的問題...</div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div className="error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="input-container">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="請輸入您的 GA4 分析問題..."
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !inputValue.trim()}>
            {isLoading ? '分析中...' : '發送'}
          </button>
        </form>

        {suggestions.length > 0 && (
          <div className="suggestions">
            <h4>建議的後續問題：</h4>
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleSuggestionClick(suggestion)}
                disabled={isLoading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default App; 