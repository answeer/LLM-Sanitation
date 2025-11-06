"""```json
    {
    "mandatory_key": {
        "Effective Date": null,
        "Expiration Date": "2027-12-31",
        "Governing Law": "中华人民共和国法律",
        "Total Contract Value": 2000000,
        "Contract Id": null,
        "Contract Title": "数据融合开发合作合同",
        "Contract Reference": null,
        "Msa Linked Contracts": [],
        "Parties": [
        "渣打银行（中国）有限公司",
        "中科软科技股份有限公司"
        ],
        "Parties Address": [
        "北京市东城区金融大街 1 号渣打大厦",
        "上海市浦东新区科苑路 100 号中科软大厦"
        ],
        "Term Type": "Fixed Term",
        "Goods Services Spend Category": "数据融合开发与AI模型训练服务",
        "Notice Period": "24小时",
        "Signature Available": false,
        "Signature Type": null,
        "Bank Signatory Name": null,
        "Bank Signatory Position": null,
        "Bank Signatory Date": null,
        "Supplier Signatory Name": null,
        "Supplier Signatory Position": null,
        "Supplier Signatory Date": null,
        "Mandatory Clause Missing": false,
        "Contract Summary": "本合同为渣打银行（中国）有限公司与中科软科技股份有限公司之间的数据融合开发合作合同。双方共同创建金融行业AI训练样本库和风险预测模型。甲方提供金融交易数据和基础设施，乙方提供行业标签库、算法技术、云算 力平台及200万元开发资金。结果数据包括金融行业风险预测模型和行业特征映射库，收益分配为甲方60%、乙方40%。合同有效期至2027年12月31日，适用中国法律，争议提交上海市闵行区人民法院或中国国际经济贸易仲裁委员会解决。"
    },
    "clause_analysis_results": {
        "Confidentiality obligations and breach remedies": {
        "Priority": "Critical",
        "Coverage_status": "Present",
        "Risk_level": "AMBER",
        "Confidence": "85%",
        "Gap Analysis and Recommendations": "第十条规定了保密义务，保密期限为5年，涵盖商业秘密保护。第十一条规定了违约责任，包括泄露商业秘密的赔偿责任。但缺乏明确的终止权条款与保密违约的关联，建议增加因重大保密违约可立即终止合同的明确条款。"
        },
        "Professional Services Data confidentiality and liability": {
        "Priority": "High",
        "Coverage_status": "Partial",
        "Risk_level": "AMBER",
        "Confidence": "70%",
        "Gap Analysis and Recommendations": "合同涉及专业服务数据（金融交易数据、行业标签库），第十条规定了保密义务，但未针对专业服务数据设置特定的责任上限。建议增加针对专业服务数据保密违约的具体责任限额条款。"
        },
        "Confidential Information disclosure restrictions": {
        "Priority": "Critical",
        "Coverage_status": "Present",
        "Risk_level": "GREEN",
        "Confidence": "90%",
        "Gap Analysis and Recommendations": "第十条明确规定各方对商业秘密的保密义务，禁止泄露或不正当使用，保密期限5年。第六条第5款规定未经书面允许不得向第三方提供结果数据（法律强制披露除外）。条款覆盖充分，符合要求。"        
        },
        "Arbitration provisions": {
        "Priority": "Medium",
        "Coverage_status": "Present",
        "Risk_level": "GREEN",
        "Confidence": "85%",
        "Gap Analysis and Recommendations": "第十三条规定争议解决机制，首先友好协商，协商不成可向上海市闵行区人民法院提起诉讼或选择中国国际经济贸易仲裁委员会（CIETAC）仲裁。提供了仲裁选项，但需双方在合同中明确选择。建议在签署 时明确选定争议解决方式。"
        },
        "Performance suspension due to uncontrollable events": {
        "Priority": "High",
        "Coverage_status": "Present",
        "Risk_level": "GREEN",
        "Confidence": "90%",
        "Gap Analysis and Recommendations": "第十一条第4款和第十二条第3款规定了不可抗力条款，因不可抗力导致根本无法继续履行时，双方可协商解除合同，违约方不承担责任。条款覆盖充分，符合标准要求。"
        },
        "English law and jurisdiction": {
        "Priority": "Medium",
        "Coverage_status": "Present",
        "Risk_level": "AMBER",
        "Confidence": "95%",
        "Gap Analysis and Recommendations": "第十三条规定适用中国法律和中国司法管辖（上海市闵行区人民法院或CIETAC仲裁），而非英国法律和英国法院管辖。对于渣打银行作为国际银行，建议评估是否需要调整为英国法律管辖以符合集团标准。"
        },
        "IP Rights Indemnity": {
        "Priority": "Critical",
        "Coverage_status": "Partial",
        "Risk_level": "AMBER",
        "Confidence": "75%",
        "Gap Analysis and Recommendations": "第九条规定各方应确保所提供产品或服务不侵犯第三方知识产权，侵权方应承担全部赔偿责任。但缺乏明确的知识产权侵权赔偿（indemnity）条款和程序。建议增加详细的知识产权赔偿义务、通知程序和抗辩权条款。"
        },
        "No transfer of IP rights": {
        "Priority": "High",
        "Coverage_status": "Present",
        "Risk_level": "GREEN",
        "Confidence": "85%",
        "Gap Analysis and Recommendations": "第六条明确规定了各方对原始数据和结果数据的权利范围和限制，原始数据仅限项目内部使用，禁止转让。第九条规定尊重知识产权。虽未明确表述"不转让知识产权"，但通过权利限制实现了类似效果。"  
        },
        "Aggregate liability cap": {
        "Priority": "Critical",
        "Coverage_status": "Missing",
        "Risk_level": "RED",
        "Confidence": "95%",
        "Gap Analysis and Recommendations": "合同缺乏总体责任上限条款。第十一条仅规定违约方应赔偿全部损失，未设置责任上限。这对双方都存在重大风险。强烈建议增加总体责任上限条款，例如限制为合同总价值或年度费用的特定倍数。"      
        },
        "Exclusion of consequential damages": {
        "Priority": "Critical",
        "Coverage_status": "Missing",
        "Risk_level": "RED",
        "Confidence": "95%",
        "Gap Analysis and Recommendations": "合同未明确排除间接损失、后果性损失、利润损失等。第十一条规定违约方应赔偿"全部损失"，可能包括间接和后果性损失，存在重大风险。强烈建议增加排除间接损失、后果性损失、利润损失等的条款。"
        },
        "Liability cap and exclusions": {
        "Priority": "Critical",
        "Coverage_status": "Missing",
        "Risk_level": "RED",
        "Confidence": "90%",
        "Gap Analysis and Recommendations": "合同缺乏全面的责任上限和排除条款。虽然第八条涉及数据安全要求，但未针对保密和数据安全违约设置特定责任上限。建议增加针对保密违约、数据安全违约的具体责任上限，以及排除间接损失的条款。"
        },
        "Termination rights and remedy periods": {
        "Priority": "High",
        "Coverage_status": "Present",
        "Risk_level": "GREEN",
        "Confidence": "85%",
        "Gap Analysis and Recommendations": "第十二条第4款规定了单方解除权，包括任一方未履行主要义务且经催告10个工作日仍未履行时可解除。第二条第3款规定数据质量问题应在24小时内响应、48小时内修复。第四条第2款规定投入问题应在5日 内补正。补救期限明确，符合要求。"
        },
        "Effect of termination and survival provisions": {
        "Priority": "High",
        "Coverage_status": "Partial",
        "Risk_level": "AMBER",
        "Confidence": "75%",
        "Gap Analysis and Recommendations": "第十条规定保密义务持续5年（超出合同期限）。第十一条规定违约责任。但合同未明确列举终止后继续有效的条款清单（如定义、责任、保密、知识产权等）。建议增加明确的存续条款清单，确保关键义务在终止后继续有效。"
        }
    },
    "validation_summary_output": {
        "status": "Conditional",
        "notes": "合同整体结构完整，涵盖了数据融合开发的主要方面。关键发现：(1) 缺乏总体责任上限条款（RED风险）；(2) 未排除间接和后果性损失（RED风险）；(3) 缺乏针对保密和数据安全的特定责任上限（RED风险）；(4) 知识产权赔偿条款不 够详细（AMBER风险）；(5) 适用中国法律而非英国法律，需评估是否符合渣打银行集团政策（AMBER风险）；(6) 缺乏明确的存续条款清单（AMBER风险）。建议：在签署前必须增加责任上限和排除间接损失条款，完善知识产权赔偿和存续条款，并评估法 律管辖选择的适当性。签署页未填写，需完成签署信息。"
    }
    }
    ```
    """
