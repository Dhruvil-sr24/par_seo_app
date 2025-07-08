import React, { useState, useEffect } from 'react';
import './App.css';

const App = () => {
  const [url, setUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState('');
  const [recentAnalyses, setRecentAnalyses] = useState([]);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  useEffect(() => {
    fetchRecentAnalyses();
  }, []);

  const fetchRecentAnalyses = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/analyses`);
      if (response.ok) {
        const data = await response.json();
        setRecentAnalyses(data.slice(0, 5));
      }
    } catch (error) {
      console.error('Failed to fetch recent analyses:', error);
    }
  };

  const handleAnalyze = async () => {
    if (!url.trim()) {
      setError('Please enter a valid URL');
      return;
    }

    setIsAnalyzing(true);
    setError('');
    setAnalysis(null);

    try {
      const response = await fetch(`${backendUrl}/api/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }

      const data = await response.json();
      setAnalysis(data);
      fetchRecentAnalyses();
    } catch (error) {
      setError(error.message || 'Failed to analyze website');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const ScoreCard = ({ title, score, color }) => (
    <div className="bg-white rounded-lg shadow-md p-6 text-center">
      <h3 className="text-lg font-semibold text-gray-800 mb-2">{title}</h3>
      <div className={`text-3xl font-bold ${color} mb-2`}>
        {Math.round(score * 100)}
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div 
          className={`h-2 rounded-full transition-all duration-300 ${color.replace('text-', 'bg-')}`}
          style={{ width: `${score * 100}%` }}
        ></div>
      </div>
    </div>
  );

  const ScreenshotGrid = ({ screenshots }) => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {screenshots.map((screenshot, index) => (
        <div key={index} className="bg-white rounded-lg shadow-md p-4">
          <h4 className="text-lg font-semibold text-gray-800 mb-2">{screenshot.device}</h4>
          <p className="text-sm text-gray-600 mb-3">{screenshot.width} x {screenshot.height}</p>
          {screenshot.screenshot ? (
            <img 
              src={screenshot.screenshot} 
              alt={`${screenshot.device} screenshot`}
              className="w-full h-48 object-cover rounded border"
            />
          ) : (
            <div className="w-full h-48 bg-gray-100 rounded border flex items-center justify-center">
              <span className="text-gray-500">Screenshot failed</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );

  const KeywordsList = ({ keywords }) => (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-xl font-semibold text-gray-800 mb-4">Top Keywords Found</h3>
      <div className="flex flex-wrap gap-2">
        {keywords.map((keyword, index) => (
          <span 
            key={index}
            className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium"
          >
            {keyword}
          </span>
        ))}
      </div>
    </div>
  );

  const BacklinksList = ({ backlinks }) => (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-xl font-semibold text-gray-800 mb-4">External Links Found</h3>
      <div className="space-y-2">
        {backlinks.slice(0, 5).map((link, index) => (
          <div key={index} className="flex items-center p-2 bg-gray-50 rounded">
            <a 
              href={link} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 text-sm truncate"
            >
              {link}
            </a>
          </div>
        ))}
      </div>
    </div>
  );

  const AIInSights = ({ suggestions }) => (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
        <span className="bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">
          AI
        </span>
        AI-Powered SEO Suggestions
      </h3>
      <div className="prose prose-sm max-w-none">
        <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 whitespace-pre-wrap">
          {suggestions}
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-100">
      {/* Header */}
      <header className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-full w-12 h-12 flex items-center justify-center">
                <span className="text-xl font-bold">SEO</span>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">AI-Powered SEO Tool</h1>
                <p className="text-gray-600">Comprehensive website analysis with AI insights</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* URL Input Section */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">
            Analyze Your Website's SEO Performance
          </h2>
          <div className="flex flex-col md:flex-row gap-4 max-w-3xl mx-auto">
            <input
              type="url"
              placeholder="Enter website URL (e.g., https://example.com)"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isAnalyzing}
            />
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-8 py-3 rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAnalyzing ? 'Analyzing...' : 'Analyze Website'}
            </button>
          </div>
          {error && (
            <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg text-center">
              {error}
            </div>
          )}
        </div>

        {/* Loading State */}
        {isAnalyzing && (
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">Analyzing Your Website...</h3>
            <p className="text-gray-600">
              This may take a moment. We're running Lighthouse tests, generating screenshots, and preparing AI insights.
            </p>
          </div>
        )}

        {/* Analysis Results */}
        {analysis && (
          <div className="space-y-8">
            {/* Performance Scores */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Performance Scores</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <ScoreCard 
                  title="Performance" 
                  score={analysis.lighthouse_score.performance} 
                  color="text-blue-600" 
                />
                <ScoreCard 
                  title="Accessibility" 
                  score={analysis.lighthouse_score.accessibility} 
                  color="text-green-600" 
                />
                <ScoreCard 
                  title="Best Practices" 
                  score={analysis.lighthouse_score.best_practices} 
                  color="text-yellow-600" 
                />
                <ScoreCard 
                  title="SEO Score" 
                  score={analysis.lighthouse_score.seo} 
                  color="text-purple-600" 
                />
              </div>
            </div>

            {/* Overall Performance */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Overall Performance</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-4xl font-bold text-blue-600 mb-2">
                    {Math.round(analysis.performance_metrics.overall_score * 100)}%
                  </div>
                  <div className="text-lg text-gray-600">Overall Score</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl font-bold text-green-600 mb-2">
                    {analysis.performance_metrics.grade}
                  </div>
                  <div className="text-lg text-gray-600">Grade</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl font-bold text-purple-600 mb-2">
                    {analysis.keywords.length}
                  </div>
                  <div className="text-lg text-gray-600">Keywords Found</div>
                </div>
              </div>
            </div>

            {/* Responsive Screenshots */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Responsive Design Testing</h2>
              <ScreenshotGrid screenshots={analysis.screenshots} />
            </div>

            {/* AI Suggestions */}
            <AIInSights suggestions={analysis.ai_suggestions} />

            {/* Keywords and Backlinks */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <KeywordsList keywords={analysis.keywords} />
              <BacklinksList backlinks={analysis.backlinks} />
            </div>
          </div>
        )}

        {/* Recent Analyses */}
        {recentAnalyses.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-6 mt-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Recent Analyses</h2>
            <div className="space-y-4">
              {recentAnalyses.map((recentAnalysis, index) => (
                <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                      <span className="text-white font-bold text-sm">
                        {Math.round(recentAnalysis.performance_metrics.overall_score * 100)}
                      </span>
                    </div>
                    <div>
                      <div className="font-semibold text-gray-800">{recentAnalysis.url}</div>
                      <div className="text-sm text-gray-600">
                        {new Date(recentAnalysis.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-2xl font-bold text-gray-600">
                    {recentAnalysis.performance_metrics.grade}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-center text-gray-600">
            <p>© 2025 AI-Powered SEO Tool. Built with React, FastAPI, and Gemini AI.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;