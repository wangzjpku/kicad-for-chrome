/**
 * Tests for Layer Calculator Service (Frontend TypeScript Version)
 */

import { calculateLayerRecommendation } from '../services/layerCalculator';

describe('LayerCalculator Frontend Service', () => {
  describe('Simple circuits', () => {
    it('should recommend 1 layer for simple LED circuit', () => {
      const result = calculateLayerRecommendation({
        requirements: 'simple LED circuit with resistor',
        components: ['R1', 'R2', 'C1'],
      });

      expect(result.layer_count).toBe(1);
      expect(result.reasons).toContain('简单电路，可使用单面板降低成本');
    });

    it('should recommend 2 layers for standard digital circuit', () => {
      const result = calculateLayerRecommendation({
        requirements: 'digital logic circuit with microcontroller',
        components: ['U1', 'R1', 'R2', 'C1', 'C2', 'LED1', 'LED2'],
      });

      expect(result.layer_count).toBe(2);
    });
  });

  describe('High speed circuits', () => {
    it('should recommend 4 layers for >1GHz signals', () => {
      const result = calculateLayerRecommendation({
        requirements: 'DDR memory interface at 1.6 GHz',
        components: ['DDR3_IC', 'U1_MCU'],
      });

      expect(result.layer_count).toBeGreaterThanOrEqual(4);
    });

    it('should recommend 6 layers for >5GHz signals', () => {
      const result = calculateLayerRecommendation({
        requirements: 'USB 3.2 and PCIe 4.0 interface at 8 GHz',
        high_speed_signals: [
          { frequency_ghz: 10 },
          { frequency_ghz: 10 },
        ],
      });

      expect(result.layer_count).toBeGreaterThanOrEqual(6);
    });
  });

  describe('USB/Ethernet detection', () => {
    it('should detect USB as high speed interface', () => {
      const result = calculateLayerRecommendation({
        requirements: 'USB-C and Ethernet interface',
        components: ['USB_IC', 'ETH_PHY'],
      });

      expect(result.layer_count).toBeGreaterThanOrEqual(4);
    });
  });

  describe('Power circuits', () => {
    it('should recommend 4 layers for multi-rail power', () => {
      const result = calculateLayerRecommendation({
        requirements: 'multi-rail power supply with 3.3V, 1.8V, 1.2V and 5V rails',
        power_rails: [
          { name: 'VDD_3V3', current_ma: 500 },
          { name: 'VDD_1V8', current_ma: 300 },
          { name: 'VDD_1V2', current_ma: 1000 },
          { name: 'VDD_5V', current_ma: 2000 },
        ],
      });

      expect(result.layer_count).toBeGreaterThanOrEqual(4);
    });

    it('should recommend 4 layers for high current (>10A)', () => {
      const result = calculateLayerRecommendation({
        requirements: 'motor driver circuit handling 15A current',
        power_rails: [
          { name: 'VMOTOR', current_ma: 15000 },
        ],
      });

      expect(result.layer_count).toBeGreaterThanOrEqual(4);
    });
  });

  describe('RF circuits', () => {
    it('should recommend 4+ layers for RF circuits', () => {
      const result = calculateLayerRecommendation({
        requirements: '2.4 GHz RF transceiver module',
        components: ['RF_IC', 'Filter', 'Antenna'],
      });

      expect(result.layer_count).toBeGreaterThanOrEqual(4);
    });
  });

  describe('Impedance control', () => {
    it('should recommend 4 layers for impedance control requirements', () => {
      const result = calculateLayerRecommendation({
        requirements: 'USB 2.0 with impedance control for 90 ohm differential',
      });

      expect(result.layer_count).toBeGreaterThanOrEqual(4);
    });
  });
});
