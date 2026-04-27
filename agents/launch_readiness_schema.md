{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "apex:launch-readiness-scorecard:v1",
  "title": "APEX Launch Readiness Scorecard",
  "description": "Structured assessment of commercial launch readiness for a J&J Innovative Medicine asset across Marketing, Medical Affairs, and Market Access dimensions. Scored from regulatory signals (FDA/EMA/NICE/CMS) plus internal readiness inputs.",
  "type": "object",
  "required": [
    "scorecard_id",
    "asset",
    "evaluation",
    "dimensions",
    "overall"
  ],
  "properties": {
    "scorecard_id": {
      "type": "string",
      "description": "Unique ID for this scorecard instance, e.g. LRS-APEX-001-2026Q2",
      "pattern": "^LRS-APEX-[0-9]{3}-[0-9]{4}Q[1-4]$"
    },
    "asset": {
      "type": "object",
      "description": "The J&J asset being assessed",
      "required": [
        "apex_id",
        "brand_name",
        "generic_name",
        "indication",
        "therapeutic_area",
        "launch_phase"
      ],
      "properties": {
        "apex_id": {
          "type": "string",
          "description": "e.g. APEX-001",
          "pattern": "^APEX-[0-9]{3}$"
        },
        "brand_name": {
          "type": "string",
          "description": "e.g. Darzalex"
        },
        "generic_name": {
          "type": "string",
          "description": "e.g. daratumumab"
        },
        "indication": {
          "type": "string",
          "description": "Specific approved or pending indication being assessed"
        },
        "therapeutic_area": {
          "type": "string",
          "enum": [
            "Oncology",
            "Immunology",
            "Neuroscience"
          ]
        },
        "launch_phase": {
          "type": "string",
          "enum": [
            "Pre-NDA/BLA",
            "Under Review",
            "PDUFA Pending",
            "Recently Approved",
            "Launch",
            "Post-Launch Expansion"
          ],
          "description": "Current lifecycle stage driving readiness urgency"
        },
        "target_launch_date": {
          "type": "string",
          "format": "date"
        },
        "geography": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "US",
              "EU5",
              "Japan",
              "Global"
            ]
          }
        }
      }
    },
    "evaluation": {
      "type": "object",
      "description": "Metadata about this specific evaluation run",
      "required": [
        "evaluated_at",
        "evaluated_by",
        "signal_sources",
        "version"
      ],
      "properties": {
        "evaluated_at": {
          "type": "string",
          "format": "date-time"
        },
        "evaluated_by": {
          "type": "string",
          "description": "Model or human evaluator ID, e.g. apex-director-v1 or analyst@jnj.com"
        },
        "version": {
          "type": "string",
          "description": "Scorecard schema version, e.g. 1.0.0"
        },
        "signal_sources": {
          "type": "array",
          "description": "Regulatory/market signal sources that informed this scorecard",
          "items": {
            "type": "object",
            "required": [
              "source",
              "signal_date",
              "signal_type"
            ],
            "properties": {
              "source": {
                "type": "string",
                "enum": [
                  "FDA",
                  "EMA",
                  "NICE",
                  "CMS",
                  "IQVIA",
                  "Internal",
                  "Competitive Intel",
                  "KOL Feedback"
                ]
              },
              "signal_date": {
                "type": "string",
                "format": "date"
              },
              "signal_type": {
                "type": "string",
                "description": "e.g. AdCom outcome, label negotiation update, CMS NCD, payer formulary decision"
              },
              "signal_summary": {
                "type": "string",
                "maxLength": 500
              },
              "impact_rating": {
                "type": "string",
                "enum": [
                  "High",
                  "Medium",
                  "Low"
                ]
              }
            }
          }
        },
        "prior_scorecard_id": {
          "type": [
            "string",
            "null"
          ],
          "description": "ID of the previous scorecard this replaces, for trend tracking"
        }
      }
    },
    "dimensions": {
      "type": "object",
      "description": "Six weighted readiness dimensions. Weights must sum to 1.0.",
      "required": [
        "market_access",
        "medical_affairs",
        "marketing_brand",
        "commercial_operations",
        "regulatory_compliance",
        "patient_support"
      ],
      "properties": {
        "market_access": {
          "$ref": "#/definitions/dimension",
          "description": "Payer strategy, formulary positioning, HEOR evidence, contracting, reimbursement pathways",
          "properties": {
            "weight": {
              "type": "number",
              "default": 0.25
            },
            "sub_scores": {
              "payer_strategy_readiness": {
                "$ref": "#/definitions/sub_score"
              },
              "formulary_positioning": {
                "$ref": "#/definitions/sub_score"
              },
              "heor_evidence_package": {
                "$ref": "#/definitions/sub_score"
              },
              "contracting_readiness": {
                "$ref": "#/definitions/sub_score"
              },
              "nice_hta_status": {
                "$ref": "#/definitions/sub_score"
              },
              "cms_coverage_pathway": {
                "$ref": "#/definitions/sub_score"
              }
            }
          }
        },
        "medical_affairs": {
          "$ref": "#/definitions/dimension",
          "description": "KOL engagement depth, MSL deployment, evidence generation, medical education readiness",
          "properties": {
            "weight": {
              "type": "number",
              "default": 0.2
            },
            "sub_scores": {
              "kol_engagement_depth": {
                "$ref": "#/definitions/sub_score"
              },
              "msl_deployment_readiness": {
                "$ref": "#/definitions/sub_score"
              },
              "evidence_generation_plan": {
                "$ref": "#/definitions/sub_score"
              },
              "publication_strategy": {
                "$ref": "#/definitions/sub_score"
              },
              "medical_education_content": {
                "$ref": "#/definitions/sub_score"
              },
              "congress_presence": {
                "$ref": "#/definitions/sub_score"
              }
            }
          }
        },
        "marketing_brand": {
          "$ref": "#/definitions/dimension",
          "description": "Brand strategy, HCP promotional materials, patient messaging, DTC/DTP readiness, share of voice plan",
          "properties": {
            "weight": {
              "type": "number",
              "default": 0.2
            },
            "sub_scores": {
              "brand_positioning_clarity": {
                "$ref": "#/definitions/sub_score"
              },
              "hcp_promo_materials_approved": {
                "$ref": "#/definitions/sub_score"
              },
              "patient_messaging_tested": {
                "$ref": "#/definitions/sub_score"
              },
              "dtc_dtp_readiness": {
                "$ref": "#/definitions/sub_score"
              },
              "digital_channel_activation": {
                "$ref": "#/definitions/sub_score"
              },
              "competitive_response_toolkit": {
                "$ref": "#/definitions/sub_score"
              }
            }
          }
        },
        "commercial_operations": {
          "$ref": "#/definitions/dimension",
          "description": "Field force sizing and deployment, training completion, CRM readiness, speaker bureau",
          "properties": {
            "weight": {
              "type": "number",
              "default": 0.15
            },
            "sub_scores": {
              "field_force_deployment": {
                "$ref": "#/definitions/sub_score"
              },
              "training_completion_rate": {
                "$ref": "#/definitions/sub_score"
              },
              "crm_data_readiness": {
                "$ref": "#/definitions/sub_score"
              },
              "speaker_bureau_activation": {
                "$ref": "#/definitions/sub_score"
              },
              "targeting_segmentation": {
                "$ref": "#/definitions/sub_score"
              }
            }
          }
        },
        "regulatory_compliance": {
          "$ref": "#/definitions/dimension",
          "description": "Approval status, label negotiation outcome, REMS if applicable, post-marketing commitments",
          "properties": {
            "weight": {
              "type": "number",
              "default": 0.12
            },
            "sub_scores": {
              "approval_status": {
                "$ref": "#/definitions/sub_score"
              },
              "label_breadth_vs_target": {
                "$ref": "#/definitions/sub_score"
              },
              "rems_readiness": {
                "$ref": "#/definitions/sub_score"
              },
              "post_marketing_commitments": {
                "$ref": "#/definitions/sub_score"
              },
              "promotional_review_readiness": {
                "$ref": "#/definitions/sub_score"
              }
            }
          }
        },
        "patient_support": {
          "$ref": "#/definitions/dimension",
          "description": "Hub services, copay support, specialty pharmacy network, adherence programs",
          "properties": {
            "weight": {
              "type": "number",
              "default": 0.08
            },
            "sub_scores": {
              "hub_services_readiness": {
                "$ref": "#/definitions/sub_score"
              },
              "copay_patient_assistance": {
                "$ref": "#/definitions/sub_score"
              },
              "specialty_pharmacy_network": {
                "$ref": "#/definitions/sub_score"
              },
              "adherence_program_design": {
                "$ref": "#/definitions/sub_score"
              }
            }
          }
        }
      }
    },
    "overall": {
      "type": "object",
      "description": "Rolled-up launch readiness verdict",
      "required": [
        "weighted_score",
        "readiness_tier",
        "top_gaps",
        "comm_ex_recommendations"
      ],
      "properties": {
        "weighted_score": {
          "type": "number",
          "minimum": 0,
          "maximum": 5,
          "description": "Weighted average of all dimension scores (0–5 scale)"
        },
        "readiness_tier": {
          "type": "string",
          "enum": [
            "Red — Not Launch Ready",
            "Amber — Conditional",
            "Green — Launch Ready",
            "Gold — Best-in-Class"
          ],
          "description": "Red <2.5 | Amber 2.5–3.4 | Green 3.5–4.4 | Gold 4.5+"
        },
        "top_gaps": {
          "type": "array",
          "maxItems": 5,
          "description": "Top-priority readiness gaps identified, ranked by launch impact",
          "items": {
            "type": "object",
            "required": [
              "dimension",
              "gap_description",
              "severity",
              "owner"
            ],
            "properties": {
              "dimension": {
                "type": "string"
              },
              "gap_description": {
                "type": "string",
                "maxLength": 300
              },
              "severity": {
                "type": "string",
                "enum": [
                  "Launch-Blocking",
                  "High",
                  "Medium",
                  "Low"
                ]
              },
              "owner": {
                "type": "string",
                "enum": [
                  "Marketing",
                  "Medical Affairs",
                  "Market Access",
                  "Commercial Ops",
                  "Regulatory",
                  "Patient Support"
                ]
              },
              "target_close_date": {
                "type": "string",
                "format": "date"
              }
            }
          }
        },
        "comm_ex_recommendations": {
          "type": "array",
          "description": "Prioritised Comm Ex actions generated by APEX Director agent",
          "items": {
            "type": "object",
            "required": [
              "recommendation_id",
              "audience",
              "action",
              "rationale",
              "urgency"
            ],
            "properties": {
              "recommendation_id": {
                "type": "string",
                "pattern": "^REC-[0-9]{3}$"
              },
              "audience": {
                "type": "string",
                "enum": [
                  "Marketing",
                  "Medical Affairs",
                  "Market Access",
                  "Leadership",
                  "Field Force"
                ]
              },
              "action": {
                "type": "string",
                "maxLength": 400,
                "description": "Specific, actionable directive in imperative voice"
              },
              "rationale": {
                "type": "string",
                "maxLength": 400,
                "description": "Signal-grounded reason — cite source (FDA/EMA/NICE/CMS/competitive)"
              },
              "urgency": {
                "type": "string",
                "enum": [
                  "Immediate (0–30d)",
                  "Near-term (30–90d)",
                  "Strategic (90d+)"
                ]
              },
              "kpi": {
                "type": "string",
                "description": "Measurable outcome to confirm action landed"
              }
            }
          }
        },
        "narrative_summary": {
          "type": "string",
          "maxLength": 1000,
          "description": "2–4 sentence executive summary of launch readiness posture and top priority"
        }
      }
    }
  },
  "definitions": {
    "dimension": {
      "type": "object",
      "required": [
        "score",
        "weight",
        "confidence",
        "rationale",
        "sub_scores"
      ],
      "properties": {
        "score": {
          "type": "number",
          "minimum": 0,
          "maximum": 5,
          "description": "Dimension readiness score: 1=Critical Gap, 2=Significant Gap, 3=Developing, 4=Strong, 5=Best-in-Class"
        },
        "weight": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "confidence": {
          "type": "string",
          "enum": [
            "High",
            "Medium",
            "Low"
          ],
          "description": "Confidence in score based on signal data quality"
        },
        "rationale": {
          "type": "string",
          "maxLength": 600,
          "description": "Evidence-based explanation of the score, citing specific signals"
        },
        "trend": {
          "type": "string",
          "enum": [
            "Improving",
            "Stable",
            "Deteriorating",
            "Not enough data"
          ],
          "description": "Vs. prior scorecard"
        },
        "sub_scores": {
          "type": "object"
        }
      }
    },
    "sub_score": {
      "type": "object",
      "required": [
        "score",
        "status"
      ],
      "properties": {
        "score": {
          "type": "number",
          "minimum": 0,
          "maximum": 5
        },
        "status": {
          "type": "string",
          "enum": [
            "Not Started",
            "In Progress",
            "At Risk",
            "On Track",
            "Complete"
          ]
        },
        "notes": {
          "type": "string",
          "maxLength": 300
        }
      }
    }
  }
}