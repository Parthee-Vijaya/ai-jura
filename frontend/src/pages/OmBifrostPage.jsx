import React from 'react';
import styled from 'styled-components';
import {
  FaLightbulb,
  FaFileUpload,
  FaMicrochip,
  FaBalanceScale,
  FaCheck,
  FaExternalLinkAlt,
} from 'react-icons/fa';

const LANDING_URL = 'https://bifrost-compliance.vercel.app';

const Page = styled.div`
  max-width: 980px;
  margin: 0 auto;
  padding: 3rem 2.5rem 5rem;
  color: ${(p) => p.theme.colors.ink};
`;

const Eyebrow = styled.div`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.72rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: ${(p) => p.theme.colors.bronze};
  font-weight: 600;
  margin-bottom: 0.9rem;
`;

const H1 = styled.h1`
  font-family: ${(p) => p.theme.fonts.serif};
  font-size: 2.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
  margin: 0 0 0.8rem;

  em { font-style: italic; color: ${(p) => p.theme.colors.primary}; }
`;

const Lead = styled.p`
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 1.12rem;
  line-height: 1.6;
  color: ${(p) => p.theme.colors.inkSoft};
  max-width: 62ch;
  margin: 0 0 2.6rem;
`;

const SectionTitle = styled.h2`
  font-family: ${(p) => p.theme.fonts.serif};
  font-size: 1.6rem;
  font-weight: 600;
  letter-spacing: -0.015em;
  margin: 0 0 0.4rem;
`;

const SectionSub = styled.p`
  font-size: 0.98rem;
  color: ${(p) => p.theme.colors.inkFaded};
  margin: 0 0 1.8rem;
  max-width: 64ch;
`;

/* ---- 4-beat flow ---- */
const Flow = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  margin: 0 0 2.8rem;

  @media (max-width: 820px) {
    grid-template-columns: 1fr 1fr;
    gap: 2rem 0;
  }
`;

const Beat = styled.div`
  text-align: center;
  padding: 0 0.9rem;
  position: relative;

  &:not(:last-child)::after {
    content: '';
    position: absolute;
    top: 32px;
    left: 64%;
    right: -36%;
    height: 2px;
    background: ${(p) => p.theme.colors.line};
    z-index: 0;
    @media (max-width: 820px) { display: none; }
  }

  .ring {
    width: 64px;
    height: 64px;
    border-radius: 18px;
    background: ${(p) => (p.$ai ? p.theme.colors.primary : p.theme.colors.paperSoft)};
    border: 1.5px solid ${(p) => (p.$ai ? p.theme.colors.primary : p.$jur ? p.theme.colors.bronze : p.theme.colors.line)};
    color: ${(p) => (p.$ai ? '#fff' : p.$jur ? p.theme.colors.bronze : p.theme.colors.primary)};
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 0.9rem;
    position: relative;
    z-index: 2;
    font-size: 1.4rem;
  }

  .lbl {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.64rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: ${(p) => (p.$ai ? p.theme.colors.primary : p.theme.colors.bronze)};
    font-weight: 600;
    margin-bottom: 0.4rem;
  }

  h3 { font-size: 1.05rem; font-weight: 600; margin: 0 0 0.4rem; }
  p { font-size: 0.85rem; color: ${(p) => p.theme.colors.inkSoft}; line-height: 1.45; margin: 0; }
`;

/* ---- 80/20 split ---- */
const Split = styled.div`
  background: ${(p) => p.theme.colors.paper};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 16px;
  padding: 1.9rem 2rem;
  margin-bottom: 2.8rem;
`;

const Bar = styled.div`
  display: flex;
  height: 56px;
  border-radius: 11px;
  overflow: hidden;
  margin-bottom: 1.4rem;
  border: 1px solid ${(p) => p.theme.colors.line};

  .ai {
    flex: 0 0 80%;
    background: ${(p) => p.theme.colors.primary};
    color: #fff;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0 1.4rem;
    font-weight: 600;
    font-size: 0.98rem;
  }
  .jur {
    flex: 1;
    background: ${(p) => p.theme.colors.bronze};
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.92rem;
    text-align: center;
    padding: 0 0.5rem;
  }
  @media (max-width: 640px) { .ai { font-size: 0.8rem; padding: 0 0.8rem; } }
`;

const Cols = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.8rem;
  @media (max-width: 720px) { grid-template-columns: 1fr; gap: 1.4rem; }
`;

const Col = styled.div`
  h4 {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 1.02rem;
    font-weight: 700;
    margin: 0 0 0.9rem;
  }
  .pct {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.74rem;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 9px;
    background: ${(p) => (p.$jur ? p.theme.colors.bronzeSoft : p.theme.colors.paperSoft)};
    color: ${(p) => (p.$jur ? p.theme.colors.bronze : p.theme.colors.primary)};
  }
  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.6rem; }
  li {
    font-size: 0.9rem;
    color: ${(p) => p.theme.colors.inkSoft};
    display: flex;
    gap: 0.6rem;
    align-items: flex-start;
    line-height: 1.4;
    svg { flex-shrink: 0; margin-top: 3px; color: ${(p) => (p.$jur ? p.theme.colors.bronze : p.theme.colors.primary)}; font-size: 0.85rem; }
  }
`;

/* ---- landing link card ---- */
const LandingCard = styled.a`
  display: flex;
  align-items: center;
  gap: 1.2rem;
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 14px;
  padding: 1.4rem 1.6rem;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;

  &:hover {
    border-color: ${(p) => p.theme.colors.primary};
    transform: translateY(-2px);
    box-shadow: 0 14px 30px -16px rgba(13, 46, 84, 0.3);
  }

  .ic {
    width: 46px;
    height: 46px;
    border-radius: 11px;
    background: ${(p) => p.theme.colors.bronzeSoft};
    color: ${(p) => p.theme.colors.bronze};
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: 1.1rem;
  }
  .txt { flex: 1; }
  .txt b { display: block; font-size: 1.02rem; font-weight: 600; margin-bottom: 0.15rem; }
  .txt span { font-size: 0.86rem; color: ${(p) => p.theme.colors.inkFaded}; }
  .arrow { color: ${(p) => p.theme.colors.primary}; font-size: 0.95rem; }
`;

export default function OmBifrostPage() {
  return (
    <Page>
      <Eyebrow>Om Bifrost · Fra ønske til jurist</Eyebrow>
      <H1>Sagen er 80&nbsp;% færdig, <em>før den lander på dit bord.</em></H1>
      <Lead>
        Bifrost vurderer kommunens AI-løsninger mod EU AI Act, GDPR og dansk særlovgivning. Et ønske om
        en AI-løsning bliver til en struktureret, gennemgået sag — automatisk. AI og en deterministisk
        regelmotor gør hovedparten af arbejdet, så juristen kan bruge tiden på det, der kræver fagligt skøn.
      </Lead>

      <SectionTitle>Sådan hænger flowet sammen</SectionTitle>
      <SectionSub>Fire trin fra et ønske opstår, til en færdig sag lander hos juristen.</SectionSub>

      <Flow>
        <Beat>
          <div className="ring"><FaLightbulb /></div>
          <div className="lbl">Det starter</div>
          <h3>Et ønske opstår</h3>
          <p>En afdeling vil tage en AI-løsning i brug.</p>
        </Beat>
        <Beat>
          <div className="ring"><FaFileUpload /></div>
          <div className="lbl">Input</div>
          <h3>Dokumenter uploades</h3>
          <p>Kontrakt, databehandleraftale og produktmateriale lægges ind.</p>
        </Beat>
        <Beat $ai>
          <div className="ring"><FaMicrochip /></div>
          <div className="lbl">80&nbsp;% automatisk</div>
          <h3>AI + regelmotor</h3>
          <p>Strukturering, vurdering, risici og udkast laves uden manuelt arbejde.</p>
        </Beat>
        <Beat $jur>
          <div className="ring"><FaBalanceScale /></div>
          <div className="lbl">De sidste 20&nbsp;%</div>
          <h3>Juristen tager over</h3>
          <p>En struktureret, gennemgået sag — klar til fagligt skøn og underskrift.</p>
        </Beat>
      </Flow>

      <SectionTitle>Hvem gør hvad</SectionTitle>
      <SectionSub>AI og den deterministiske regelmotor klarer hovedparten, så juristen kan koncentrere sig om skønnet.</SectionSub>

      <Split>
        <Bar>
          <div className="ai"><FaMicrochip /> 80&nbsp;% · AI + deterministisk regelmotor</div>
          <div className="jur">20&nbsp;% · jurist</div>
        </Bar>
        <Cols>
          <Col>
            <h4>Gjort automatisk <span className="pct">80&nbsp;%</span></h4>
            <ul>
              <li><FaCheck /> Intake struktureret fra fritekst eller dokumenter</li>
              <li><FaCheck /> Fakta udtrukket fra kontrakt og databehandleraftale</li>
              <li><FaCheck /> Compliance vurderet mod faste regler med lovcitater</li>
              <li><FaCheck /> Risici identificeret og scoret Lav → Høj</li>
              <li><FaCheck /> Risikovurdering + DPIA-udkast på kommunens skabelon</li>
              <li><FaCheck /> Opfølgende spørgsmål stillet ud fra Datatilsynets skabeloner</li>
            </ul>
          </Col>
          <Col $jur>
            <h4>Forbeholdt juristen <span className="pct">20&nbsp;%</span></h4>
            <ul>
              <li><FaCheck /> Det faglige skøn, som faste regler ikke kan afgøre</li>
              <li><FaCheck /> Den lokale kontekst, kun kommunen kender</li>
              <li><FaCheck /> Endelig stillingtagen og prioritering</li>
              <li><FaCheck /> Ansvar, godkendelse og underskrift</li>
            </ul>
          </Col>
        </Cols>
      </Split>

      <LandingCard href={LANDING_URL} target="_blank" rel="noopener noreferrer">
        <div className="ic"><FaExternalLinkAlt /></div>
        <div className="txt">
          <b>Se den fulde oplysningsside om løsningen</b>
          <span>Hele flowet trin for trin, datasikkerhed og baggrund — åbnes i ny fane</span>
        </div>
        <FaExternalLinkAlt className="arrow" />
      </LandingCard>
    </Page>
  );
}
