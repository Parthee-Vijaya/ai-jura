import React, { useState } from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { useForm } from 'react-hook-form';
import { toast } from 'react-hot-toast';
import {
  FaRocket,
  FaCheckCircle,
  FaExclamationTriangle,
  FaTimesCircle,
  FaSpinner
} from 'react-icons/fa';
import axios from 'axios';

const QuickCheckContainer = styled.div`
  max-width: 800px;
  margin: 0 auto;
`;

const PageHeader = styled.div`
  text-align: center;
  margin-bottom: 2rem;

  h1 {
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
  }

  p {
    color: ${props => props.theme.colors.gray[600]};
    font-size: 1.1rem;
  }
`;

const CheckForm = styled.form`
  background: white;
  padding: 2rem;
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};
  margin-bottom: 2rem;
`;

const FormRow = styled.div`
  display: grid;
  grid-template-columns: ${props => props.columns || '1fr'};
  gap: 1.5rem;
  margin-bottom: 1.5rem;
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  label {
    font-weight: 600;
    color: ${props => props.theme.colors.gray[700]};
  }
`;

const Input = styled.input`
  padding: 0.75rem;
  border: 2px solid ${props => props.theme.colors.gray[300]};
  border-radius: ${props => props.theme.borderRadius};
  font-size: 1rem;
  transition: border-color 0.2s ease;

  &:focus {
    border-color: ${props => props.theme.colors.primary};
    outline: none;
  }
`;

const TextArea = styled.textarea`
  padding: 0.75rem;
  border: 2px solid ${props => props.theme.colors.gray[300]};
  border-radius: ${props => props.theme.borderRadius};
  font-size: 1rem;
  min-height: 100px;
  resize: vertical;
  font-family: inherit;
  transition: border-color 0.2s ease;

  &:focus {
    border-color: ${props => props.theme.colors.primary};
    outline: none;
  }
`;

const Select = styled.select`
  padding: 0.75rem;
  border: 2px solid ${props => props.theme.colors.gray[300]};
  border-radius: ${props => props.theme.borderRadius};
  font-size: 1rem;
  background: white;
  transition: border-color 0.2s ease;

  &:focus {
    border-color: ${props => props.theme.colors.primary};
    outline: none;
  }
`;

const CheckboxGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
`;

const CheckboxItem = styled.label`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;

  input[type="checkbox"] {
    width: 18px;
    height: 18px;
    accent-color: ${props => props.theme.colors.primary};
  }

  span {
    color: ${props => props.theme.colors.gray[700]};
  }
`;

const SubmitButton = styled.button`
  background: ${props => props.theme.colors.primary};
  color: white;
  border: none;
  padding: 1rem 2rem;
  border-radius: ${props => props.theme.borderRadius};
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
  width: 100%;

  &:hover {
    background: ${props => props.theme.colors.primary}dd;
    transform: translateY(-1px);
  }

  &:disabled {
    background: ${props => props.theme.colors.gray[400]};
    cursor: not-allowed;
    transform: none;
  }
`;

const ResultsContainer = styled(motion.div)`
  background: white;
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};
  overflow: hidden;
`;

const ResultsHeader = styled.div`
  background: ${props => props.theme.colors.success};
  color: white;
  padding: 1.5rem 2rem;
  text-align: center;

  h2 {
    margin: 0 0 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  p {
    margin: 0;
    opacity: 0.9;
  }
`;

const ResultsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  padding: 2rem;
`;

const ResultCard = styled.div`
  text-align: center;

  .icon {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 1rem;
    font-size: 24px;
  }

  .high-risk .icon {
    background: ${props => props.theme.colors.danger}20;
    color: ${props => props.theme.colors.danger};
  }

  .medium-risk .icon {
    background: ${props => props.theme.colors.warning}20;
    color: ${props => props.theme.colors.warning};
  }

  .low-risk .icon {
    background: ${props => props.theme.colors.success}20;
    color: ${props => props.theme.colors.success};
  }

  h3 {
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
  }

  .value {
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }

  .description {
    color: ${props => props.theme.colors.gray[600]};
    font-size: 0.875rem;
  }
`;

const DetailsSection = styled.div`
  padding: 2rem;
  border-top: 1px solid ${props => props.theme.colors.gray[200]};

  h3 {
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 1rem;
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  li {
    padding: 0.5rem 0;
    color: ${props => props.theme.colors.gray[700]};
    border-bottom: 1px solid ${props => props.theme.colors.gray[100]};

    &:last-child {
      border-bottom: none;
    }

    &:before {
      content: "• ";
      color: ${props => props.theme.colors.primary};
      font-weight: bold;
    }
  }
`;

const QuickCheckPage = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);

  const { register, handleSubmit, formState: { errors } } = useForm();

  const aiTypes = [
    { value: 'generative_ai', label: 'Generativ AI' },
    { value: 'predictive_ai', label: 'Prædiktiv AI' },
    { value: 'classification', label: 'Klassifikation' },
    { value: 'recommendation', label: 'Anbefalingssystem' },
    { value: 'computer_vision', label: 'Computer Vision' },
    { value: 'nlp', label: 'Naturlig Sprogbehandling' },
    { value: 'robotics', label: 'Robotik' },
    { value: 'other', label: 'Andet' }
  ];

  const sectors = [
    'Sundhed',
    'Finans',
    'Uddannelse',
    'Beskæftigelse',
    'Offentlig sektor',
    'Teknologi',
    'Detail',
    'Produktion',
    'Andet'
  ];

  const onSubmit = async (data) => {
    setIsLoading(true);

    try {
      const response = await axios.post('/api/compliance/hurtig-tjek', {
        beskrivelse: data.beskrivelse,
        ai_type: data.ai_type,
        sektor: data.sektor,
        behandler_persondata: data.behandler_persondata || false,
        automatiserede_beslutninger: data.automatiserede_beslutninger || false
      });

      setResults(response.data);
      toast.success('Hurtig tjek gennemført!');
    } catch (error) {
      console.error('Hurtig tjek fejl:', error);
      toast.error('Der opstod en fejl. Prøv igen.');
    } finally {
      setIsLoading(false);
    }
  };

  const getRiskIcon = (riskLevel) => {
    switch (riskLevel) {
      case 'unacceptable':
      case 'high':
        return FaTimesCircle;
      case 'limited':
        return FaExclamationTriangle;
      case 'minimal':
        return FaCheckCircle;
      default:
        return FaCheckCircle;
    }
  };

  const getRiskClass = (riskLevel) => {
    switch (riskLevel) {
      case 'unacceptable':
      case 'high':
        return 'high-risk';
      case 'limited':
        return 'medium-risk';
      case 'minimal':
        return 'low-risk';
      default:
        return 'low-risk';
    }
  };

  const getRiskText = (riskLevel) => {
    switch (riskLevel) {
      case 'unacceptable':
        return 'Uacceptabel';
      case 'high':
        return 'Høj';
      case 'limited':
        return 'Begrænset';
      case 'minimal':
        return 'Minimal';
      default:
        return 'Ukendt';
    }
  };

  return (
    <QuickCheckContainer>
      <PageHeader>
        <h1>⚡ Hurtig Compliance Tjek</h1>
        <p>Få øjeblikkelig feedback på dit AI-systems compliance status</p>
      </PageHeader>

      <CheckForm onSubmit={handleSubmit(onSubmit)}>
        <FormRow>
          <FormGroup>
            <label htmlFor="beskrivelse">Beskriv dit AI-system *</label>
            <TextArea
              {...register('beskrivelse', { required: 'Beskrivelse er påkrævet' })}
              placeholder="F.eks. AI-drevet rekrutteringsværktøj der screener CV'er og rangerer kandidater"
            />
            {errors.beskrivelse && (
              <span style={{ color: 'red', fontSize: '0.875rem' }}>
                {errors.beskrivelse.message}
              </span>
            )}
          </FormGroup>
        </FormRow>

        <FormRow columns="1fr 1fr">
          <FormGroup>
            <label htmlFor="ai_type">AI System Type *</label>
            <Select {...register('ai_type', { required: 'AI type er påkrævet' })}>
              <option value="">Vælg type...</option>
              {aiTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </Select>
            {errors.ai_type && (
              <span style={{ color: 'red', fontSize: '0.875rem' }}>
                {errors.ai_type.message}
              </span>
            )}
          </FormGroup>

          <FormGroup>
            <label htmlFor="sektor">Branche/Sektor *</label>
            <Select {...register('sektor', { required: 'Sektor er påkrævet' })}>
              <option value="">Vælg sektor...</option>
              {sectors.map(sector => (
                <option key={sector} value={sector}>
                  {sector}
                </option>
              ))}
            </Select>
            {errors.sektor && (
              <span style={{ color: 'red', fontSize: '0.875rem' }}>
                {errors.sektor.message}
              </span>
            )}
          </FormGroup>
        </FormRow>

        <FormRow>
          <FormGroup>
            <label>Databehandling</label>
            <CheckboxGroup>
              <CheckboxItem>
                <input
                  type="checkbox"
                  {...register('behandler_persondata')}
                />
                <span>Behandler personoplysninger</span>
              </CheckboxItem>
              <CheckboxItem>
                <input
                  type="checkbox"
                  {...register('automatiserede_beslutninger')}
                />
                <span>Træffer automatiserede beslutninger med juridiske eller betydelige konsekvenser</span>
              </CheckboxItem>
            </CheckboxGroup>
          </FormGroup>
        </FormRow>

        <SubmitButton type="submit" disabled={isLoading}>
          {isLoading ? (
            <>
              <FaSpinner className="spinner" style={{ animation: 'spin 1s linear infinite' }} />
              Analyserer...
            </>
          ) : (
            <>
              <FaRocket />
              Kør Hurtig Tjek
            </>
          )}
        </SubmitButton>
      </CheckForm>

      {results && (
        <ResultsContainer
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <ResultsHeader>
            <h2>
              <FaCheckCircle />
              Hurtig tjek gennemført!
            </h2>
            <p>Her er en øjeblikkelig analyse af dit AI-system</p>
          </ResultsHeader>

          <ResultsGrid>
            <ResultCard>
              <div className={getRiskClass(results.ai_act?.risk_level)}>
                <div className="icon">
                  {React.createElement(getRiskIcon(results.ai_act?.risk_level))}
                </div>
              </div>
              <h3>AI Act Risikoniveau</h3>
              <div className="value">
                {getRiskText(results.ai_act?.risk_level)}
              </div>
              <div className="description">
                Klassifikation jf. EU AI Act
              </div>
            </ResultCard>

            <ResultCard>
              <div className={results.gdpr?.relevant ? 'high-risk' : 'low-risk'}>
                <div className="icon">
                  {results.gdpr?.relevant ? <FaExclamationTriangle /> : <FaCheckCircle />}
                </div>
              </div>
              <h3>GDPR Anvendelig</h3>
              <div className="value">
                {results.gdpr?.relevant ? 'Ja' : 'Nej'}
              </div>
              <div className="description">
                Behandling af personoplysninger
              </div>
            </ResultCard>

            <ResultCard>
              <div className={results.needs_full_assessment ? 'medium-risk' : 'low-risk'}>
                <div className="icon">
                  {results.needs_full_assessment ? <FaExclamationTriangle /> : <FaCheckCircle />}
                </div>
              </div>
              <h3>Fuld Analyse Nødvendig</h3>
              <div className="value">
                {results.needs_full_assessment ? 'Ja' : 'Nej'}
              </div>
              <div className="description">
                Omfattende analyse anbefalet
              </div>
            </ResultCard>
          </ResultsGrid>

          {results.ai_act?.reasons && (
            <DetailsSection>
              <h3>AI Act Analyse</h3>
              <ul>
                {results.ai_act.reasons.map((reason, index) => (
                  <li key={index}>{reason}</li>
                ))}
              </ul>
            </DetailsSection>
          )}

          {results.quick_recommendations && (
            <DetailsSection>
              <h3>Hurtige Anbefalinger</h3>
              <ul>
                {results.quick_recommendations.map((rec, index) => (
                  <li key={index}>{rec}</li>
                ))}
              </ul>
            </DetailsSection>
          )}
        </ResultsContainer>
      )}
    </QuickCheckContainer>
  );
};

export default QuickCheckPage;