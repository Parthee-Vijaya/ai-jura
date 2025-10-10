import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FaCheckCircle,
  FaExclamationTriangle,
  FaTimesCircle,
  FaSpinner,
  FaServer,
  FaDatabase,
  FaSearch,
  FaRobot,
  FaChevronDown,
  FaChevronUp,
  FaLightbulb
} from 'react-icons/fa';
import axios from 'axios';

const Card = styled(motion.div)`
  background: ${props => props.theme.colors.surface};
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};
  padding: 1.5rem;
  margin-bottom: 1.5rem;
`;

const CardHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  cursor: pointer;
  user-select: none;

  h3 {
    margin: 0;
    color: ${props => props.theme.colors.gray[800]};
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
`;

const StatusGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
`;

const ServiceCard = styled(motion.div)`
  background: ${props => {
    if (props.$status === 'healthy') return '#d1fae5';
    if (props.$status === 'degraded') return '#fef3c7';
    if (props.$status === 'down') return '#fee2e2';
    return '#f8fafc';
  }};
  border-left: 4px solid ${props => {
    if (props.$status === 'healthy') return '#059669';
    if (props.$status === 'degraded') return '#f59e0b';
    if (props.$status === 'down') return '#dc2626';
    return '#cbd5e1';
  }};
  border-radius: 8px;
  padding: 1rem;
  position: relative;

  .service-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;

    .icon {
      font-size: 1.5rem;
      color: ${props => {
        if (props.$status === 'healthy') return '#059669';
        if (props.$status === 'degraded') return '#f59e0b';
        if (props.$status === 'down') return '#dc2626';
        return '#64748b';
      }};
    }

    h4 {
      margin: 0;
      font-size: 1rem;
      color: ${props => props.theme.colors.gray[800]};
    }
  }

  .service-details {
    font-size: 0.875rem;
    color: ${props => props.theme.colors.gray[600]};
    margin-bottom: 0.5rem;

    .detail-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.25rem;

      .label {
        font-weight: 600;
      }

      .value {
        font-family: 'Courier New', monospace;
      }
    }
  }

  .error-message {
    background: rgba(220, 38, 38, 0.1);
    border-radius: 4px;
    padding: 0.5rem;
    font-size: 0.75rem;
    color: #991b1b;
    margin-top: 0.5rem;
    font-family: 'Courier New', monospace;
  }
`;

const SolutionPanel = styled(motion.div)`
  background: linear-gradient(135deg, rgba(201, 68, 22, 0.05), rgba(232, 90, 40, 0.03));
  border: 1px solid rgba(201, 68, 22, 0.15);
  border-radius: 8px;
  padding: 1.5rem;
  margin-top: 1rem;

  .solution-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;

    svg {
      color: #C94416;
      font-size: 1.5rem;
    }

    h4 {
      margin: 0;
      color: ${props => props.theme.colors.gray[800]};
    }
  }

  .solution-content {
    font-size: 0.875rem;
    color: ${props => props.theme.colors.gray[700]};
    line-height: 1.6;

    h5 {
      margin: 1rem 0 0.5rem;
      color: ${props => props.theme.colors.gray[800]};
      font-size: 0.95rem;
    }

    ul {
      margin: 0.5rem 0;
      padding-left: 1.5rem;

      li {
        margin-bottom: 0.5rem;
      }
    }

    pre {
      background: ${props => props.theme.colors.gray[100]};
      padding: 0.75rem;
      border-radius: 4px;
      overflow-x: auto;
      font-size: 0.8rem;
    }
  }

  .loading {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: ${props => props.theme.colors.gray[600]};
    font-style: italic;

    svg {
      animation: spin 1s linear infinite;
    }
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const RefreshButton = styled.button`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: ${props => props.theme.colors.primary};
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: ${props => props.theme.colors.primaryDark};
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const SystemHealthCard = () => {
  const [expanded, setExpanded] = useState(true);
  const [checking, setChecking] = useState(false);
  const [services, setServices] = useState({
    backend: { status: 'checking', responseTime: null, error: null },
    database: { status: 'checking', responseTime: null, error: null },
    websearch: { status: 'checking', responseTime: null, error: null },
    llm: { status: 'checking', responseTime: null, error: null }
  });
  const [aiSolution, setAiSolution] = useState(null);
  const [loadingSolution, setLoadingSolution] = useState(false);

  const checkHealth = async () => {
    setChecking(true);
    const results = {};

    // Check Backend
    try {
      const start = Date.now();
      const response = await axios.get('/api/version', { timeout: 5000 });
      const responseTime = Date.now() - start;
      results.backend = {
        status: response.status === 200 ? 'healthy' : 'degraded',
        responseTime,
        version: response.data.version,
        error: null
      };
    } catch (error) {
      results.backend = {
        status: 'down',
        responseTime: null,
        error: error.message,
        details: error.response?.data || null
      };
    }

    // Check Database
    try {
      const start = Date.now();
      const response = await axios.get('/api/health/database', { timeout: 5000 });
      const responseTime = Date.now() - start;
      results.database = {
        status: response.data.healthy ? 'healthy' : 'degraded',
        responseTime,
        error: null,
        records: response.data.record_count
      };
    } catch (error) {
      results.database = {
        status: 'down',
        responseTime: null,
        error: error.message
      };
    }

    // Check Web Search
    try {
      const start = Date.now();
      const response = await axios.post('/api/compliance/test-search', {
        query: 'GDPR test'
      }, { timeout: 10000 });
      const responseTime = Date.now() - start;
      results.websearch = {
        status: response.data.success ? 'healthy' : 'degraded',
        responseTime,
        error: null,
        resultsFound: response.data.results_count
      };
    } catch (error) {
      results.websearch = {
        status: 'down',
        responseTime: null,
        error: error.message
      };
    }

    // Check LLM
    try {
      const start = Date.now();
      const response = await axios.post('/api/compliance/test-llm', {
        prompt: 'Test'
      }, { timeout: 15000 });
      const responseTime = Date.now() - start;
      results.llm = {
        status: response.data.success ? 'healthy' : 'degraded',
        responseTime,
        error: null,
        model: response.data.model
      };
    } catch (error) {
      results.llm = {
        status: 'down',
        responseTime: null,
        error: error.message
      };
    }

    setServices(results);
    setChecking(false);

    // If any service is down, fetch AI solution
    const downServices = Object.entries(results).filter(([_, service]) => service.status === 'down');
    if (downServices.length > 0) {
      fetchAISolution(downServices);
    } else {
      setAiSolution(null);
    }
  };

  const fetchAISolution = async (downServices) => {
    setLoadingSolution(true);
    try {
      const serviceNames = downServices.map(([name, _]) => name).join(', ');
      const errors = downServices.map(([name, service]) => `${name}: ${service.error}`).join('; ');

      const response = await axios.post('/api/ai/diagnose-issue', {
        services: serviceNames,
        errors: errors,
        context: 'Judge Dredd compliance system'
      });

      setAiSolution(response.data.solution);
    } catch (error) {
      setAiSolution({
        diagnosis: 'Kunne ikke hente AI-løsning',
        steps: ['Tjek manuelt logs', 'Genstart services'],
        resources: []
      });
    } finally {
      setLoadingSolution(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 60000); // Check every minute
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status) => {
    if (status === 'healthy') return <FaCheckCircle />;
    if (status === 'degraded') return <FaExclamationTriangle />;
    if (status === 'down') return <FaTimesCircle />;
    return <FaSpinner />;
  };

  const getServiceIcon = (serviceName) => {
    if (serviceName === 'backend') return <FaServer />;
    if (serviceName === 'database') return <FaDatabase />;
    if (serviceName === 'websearch') return <FaSearch />;
    if (serviceName === 'llm') return <FaRobot />;
    return <FaServer />;
  };

  return (
    <Card
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <CardHeader onClick={() => setExpanded(!expanded)}>
        <h3>
          {checking ? <FaSpinner style={{ animation: 'spin 1s linear infinite' }} /> : getStatusIcon(
            Object.values(services).every(s => s.status === 'healthy') ? 'healthy' :
            Object.values(services).some(s => s.status === 'down') ? 'down' : 'degraded'
          )}
          System Sundhedstjek
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <RefreshButton onClick={(e) => { e.stopPropagation(); checkHealth(); }} disabled={checking}>
            <FaSpinner style={{ animation: checking ? 'spin 1s linear infinite' : 'none' }} />
            Opdater
          </RefreshButton>
          {expanded ? <FaChevronUp /> : <FaChevronDown />}
        </div>
      </CardHeader>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <StatusGrid>
              {Object.entries(services).map(([name, service]) => (
                <ServiceCard
                  key={name}
                  $status={service.status}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="service-header">
                    <div className="icon">
                      {getServiceIcon(name)}
                    </div>
                    <h4>{name.charAt(0).toUpperCase() + name.slice(1)}</h4>
                  </div>

                  <div className="service-details">
                    <div className="detail-row">
                      <span className="label">Status:</span>
                      <span className="value" style={{
                        color: service.status === 'healthy' ? '#059669' :
                               service.status === 'degraded' ? '#f59e0b' : '#dc2626'
                      }}>
                        {service.status === 'healthy' ? '✓ Healthy' :
                         service.status === 'degraded' ? '⚠ Degraded' :
                         service.status === 'down' ? '✗ Down' : '⟳ Checking'}
                      </span>
                    </div>

                    {service.responseTime && (
                      <div className="detail-row">
                        <span className="label">Response:</span>
                        <span className="value">{service.responseTime}ms</span>
                      </div>
                    )}

                    {service.version && (
                      <div className="detail-row">
                        <span className="label">Version:</span>
                        <span className="value">{service.version}</span>
                      </div>
                    )}

                    {service.records !== undefined && (
                      <div className="detail-row">
                        <span className="label">Records:</span>
                        <span className="value">{service.records}</span>
                      </div>
                    )}

                    {service.model && (
                      <div className="detail-row">
                        <span className="label">Model:</span>
                        <span className="value">{service.model}</span>
                      </div>
                    )}
                  </div>

                  {service.error && (
                    <div className="error-message">
                      ⚠ {service.error}
                    </div>
                  )}
                </ServiceCard>
              ))}
            </StatusGrid>

            {/* AI Solution Panel */}
            {(loadingSolution || aiSolution) && (
              <SolutionPanel
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="solution-header">
                  <FaLightbulb />
                  <h4>AI-baseret Løsningsforslag</h4>
                </div>

                {loadingSolution ? (
                  <div className="loading">
                    <FaSpinner />
                    <span>Analyserer problem og søger efter løsninger online...</span>
                  </div>
                ) : aiSolution && (
                  <div className="solution-content">
                    <h5>📊 Diagnose:</h5>
                    <p>{aiSolution.diagnosis}</p>

                    <h5>🔧 Løsningsskridt:</h5>
                    <ul>
                      {aiSolution.steps?.map((step, idx) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ul>

                    {aiSolution.command && (
                      <>
                        <h5>💻 Kommando:</h5>
                        <pre>{aiSolution.command}</pre>
                      </>
                    )}

                    {aiSolution.resources && aiSolution.resources.length > 0 && (
                      <>
                        <h5>🔗 Relevante Ressourcer:</h5>
                        <ul>
                          {aiSolution.resources.map((resource, idx) => (
                            <li key={idx}>
                              <a href={resource.url} target="_blank" rel="noopener noreferrer">
                                {resource.title}
                              </a>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                )}
              </SolutionPanel>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
};

export default SystemHealthCard;
