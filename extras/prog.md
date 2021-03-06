# ความก้าวหน้าการดำเนินงาน

## Database

### รายละเอียดการพัฒนา

ในการพัฒนา ได้มีการสร้างฐานข้อมูลเพื่อใช้ในการเก็บข้อมูลจุดความร้อน
โดยใช้ InfluxDB เป็นระบบฐานข้อมูลสำหรับงานนี้
โดยทำการติดตั้งแบบส่วนตัวสำหรับการใช้งานกับระบบนี้เท่านั้น

ข้อมูลที่ทำการจัดเก็บประกอบด้วยจุดความร้อนดิบที่อยู่ในประเทศไทยและพื้นที่ใกล้เคียงที่นำมาจาก FIRMS

### อุปสรรคในการพัฒนา

ในระหว่างการพัฒนา ได้พบปัญหาในการทำการร้องขอข้อมูลจากระบบฐานข้อมูล เนื่องจาก InfluxDB
มีภาษาที่ใช้ในการร้องขอข้อมูลได้สองแบบ
โดยแบบแรกเป็น InfluxQL ซึ่งมีลักษณะคล้ายคลึงกับภาษาประเภท SQL และอีกแบบคือภาษา Flux
ซึ่งเป็นภาษาพิเศษที่สร้างขึ้นมาเพื่อใช้กับการประมวลผลและร้องขอข้อมูลจาก InfluxDB โดยเฉพาะ
ซึ่งข้อดีในการใช้ InfluxQL นั้นคือเรียบง่าย มีลักษณะคล้ายคลึงกับภาษากลุ่ม SQL
ทำให้สามารถทำการร้องขอข้อมูลได้เร็วกว่า แต่การใช้ Flux
ในการร้องขอข้อมูลนั้นสามารถทำการประมวลผลข้อมูลเบื้องต้นได้ที่ระบบฐานข้อมูลเลย
ทำให้สามารถทำการร้องขอข้อมูลที่เกี่ยวข้องได้แม่นยำขึ้น
ลดการประมวลผลที่ไม่เกี่ยวข้องกับงานประมวลผลหลักได้
แต่นั่นก็ทำให้การเขียนคำสั่งร้องขอข้อมูลนั้นมีความยาวและซับซ้อนเพิ่มขึ้นอย่างมาก

### แนวทางแก้ไขปัญหา

ทำการประเมินว่าการประมวลผลข้อมูลเบื้องต้นที่ใช้นั้น สามารถนำมาประมวลผลที่ด้านผู้รับข้อมูลแทนได้หรือไม่
ดูว่าการประมวลผลด้านระบบฐานข้อมูลหรือด้านผู้รับนั้น แบบไหนที่ได้ประสิทธิภาพโดยรวมได้ดีกว่า
แบบไหนมีความซับซ้อนน้อยกว่า และความซับซ้อนต่อผลที่ได้นั้นคุ้มค่าที่จะใช้หรือไม่ 
และทำการเลือกวิธีที่เหมาะสมกับงานต่อไป

## FIRMS NRT Data Acquisition and Preprocessing

### รายละเอียดการดำเนินงาน

ในโครงงานนี้ มีการใช้ข้อมูลจุดความร้อนจาก FIRMS เป็นข้อมูลตั้งต้นในการทำนายหาพื้นที่ที่เป็นไฟป่าและ
การทำงานอื่นๆที่เกี่ยวข้อง แต่ก่อนหน้าที่จะนำข้อมูลมาใช้นั้น ต้องมีการประมวลผลข้อมูลเบื่องต้นเพื่อนำข้อมูล
ที่ไม่เกี่ยวข้องออกไปเสียก่อน

ได้ทำการพัฒนาคำสั่งที่สามารถใช้ในการร้องขอข้อมูล Near Real Time (NRT)
โดยสามารถเลือกดาวเทียมเป็นต้นทางของข้อมูลจุดความร้อนได้
พร้อมทั้งวิธีการประมวลผลข้อมูลเบื้องต้นเพื่อให้ได้ข้อมูลที่เกี่ยวข้อง อย่างเช่นการสร้าง Timestamp
ของจุดข้อมูลที่ถูกต้อง และการกรองข้อมูลให้เหลือข้อมูลที่อยู่ภายในขอบเขต Bounding Box
ของประเทศไทยเท่านั้น เนื่องจากข้อมูลที่ได้มาจากการร้องขอนั้นมีขอบเขตครอบคลุมทั้งพื้นที่ทวีบเอเชีย
ทางตะวันออกเฉียงใต้ ซึ่งเยอะเกินต้องการ
พร้อมทั้งการนำข้อมูลไปจัดเก็บลงระบบฐานข้อมูลเนื่องจากข้อจำกัดของลักษณะของข้อมูลที่ใช้ในระบบฐานข้อมูล

### อุปสรรคในการพัฒนา

อุปสรรคในการพัฒนาส่วนนี้ ได้แก่การที่ข้อมูลบางส่วนนั้นมีประเภทของข้อมูลไม่ตรงกัน อย่างเช่นข้อมูล
ค่าความมั่นใจในจุดความร้อนที่วัดได้ (confidence) ในข้อมูลประเภท NRT นั้นจะมีการจัดกลุ่มข้อมูล
เป็นประเภทชัดเจนโดยแสดงผ่านตัวอักษร แต่ในข้อมูลที่เป็นข้อมูลเก่านั้น ค่าที่ได้จะเป็นค่าตัวเลข
ซึ่งเมื่อทำการจัดเก็บลงฐานข้อมูลจะเกิดการขัดแย้งกันของประเภทข้อมูล ทำให้ไม่สามารถจัดเก็บข้อมูลนั้นได้

### แนวทางแก้ไขปัญหา

แนวทางแก้ไขปัญหาที่คาดไว้ คือการกำหนดลักษณะและประเภทค่าของข้อมูลให้ชัดเจน โดยถ้าหากพบค่าที่
มีประเภทค่าไม่ตรงกัน ให้ทำการแปลงข้อมูลจากประเภทหนึ่งไปยังอีกประเภทหนึ่งทั้งหมด โดยใช้วิธีการ
ต่างๆเช่นการจัดกลุ่มค่าเป็นประเภทเพื่อให้มีลักษณะเหมือนกันทั้งหมด ก่อนทำการจัดเก็บต่อไป

## Web Application

### รายละเอียดการดำเนินงาน

### อุปสรรคในการพัฒนา

### แนวทางแก้ไขปัญหา

## Clustering

### รายละเอียดการดำเนินงาน

หลังจากได้ข้อมูลมาแล้ว การประมวลผลหลักแรกที่ทำคือการพยายามทำการจับกลุ่มจุดความร้อน เพื่อหาว่า
บริเวณไหนที่มีจุดความร้อนอยู่ในบริเวณใกล้เคียงในปริมาณมากบ้าง เพื่อประกอบการระบุบริเวณที่คาดว่า
จะมีไฟป่าเกิดขึ้น

ได้ทำการพัฒนากระบวนการจัดกลุ่มข้อมูลโดยใช้ DBSCAN เป็นวิธีในการจัดกลุ่ม โดยวิธีนี้สามารถทำการ
จัดกลุ่มจุดที่อยู่ใกล่เคียงกันได้โดยที่ไม่ต้องระบุจำนวนกลุ่มของจุดข้อมูลที่มีอยู่ในข้อมูลทั้งหมด
โดยประเมินจากการมีของจุดข้อมูลอื่นภายในรัศมีที่ระบุจากจุดหนึ่งๆ

### อุปสรรคในการพัฒนา

การเลือกรัศมีที่เหมาะสมในการจัดกลุ่มข้อมูล เพื่อให้สามารถจัดกลุ่มข้อมูลเพื่อหาพื้นที่ไฟป่าได้ตรงกับพื้นที่
ที่เกิดไฟป่าขึ้นจริงที่สุด

### แนวทางแก้ไขปัญหา

## Region of Interest

### รายละเอียดการดำเนินงาน

หนึ่งในความสามารถที่ต้องการของระบบที่พัฒนานี้ คือการที่สามารถนำไปใช้กับพื้นที่เฉพาะจุดได้
อย่างเช่นการนำไปใช้กับพื้นที่ป่าพรุควนเคร็ง อยู่ที่จังหวัดนครศรีธรรมราช
ซึ่งมักประสบปัญหาไฟป่าที่เกิดขึ้นภายในเกือบทุกปี หากสามารถนำระบบนี้ไปประยุกต์ใช้ได้
ก็จะช่วยให้เจ้าหน้าที่ทำการป้องกันและดับไฟป่าที่เกิดขึ้นได้อย่างทันท่วงที

ในขณะนี้ ได้ทำการพัฒนาระบบให้สามารถทำการกรองจุดข้อมูลเพื่อให้เหลือเพียงเฉพาะจุดที่อยู่ภายใน
บริเวณที่สนใจได้ และนำจุดข้อมูลที่ได้ไปทำการประมวลผลหาไฟป่าต่อไป
สามารถทำการเพิ่มพื้นที่ที่สนใจอื่นๆ ได้หากต้องการ
โดยการพัฒนาระบบต่อจากนี้จะยึดกับพื้นที่ป่าควนเคร็งเป็นหลัก

### อุปสรรคในการพัฒนา

ในการพัฒนาโดยอิงกับพื้นที่ป่าควนเคร็งนั้นมีความจำเป็นที่จะต้องรู้พื้นที่ป่าชัดเจนจึงจะดำเนินงานต่อได้
แต่ว่าผู้พัฒนาไม่สามารถค้นหาข้อมูลพื้นที่ป่าควนเคร็งโดยตรงได้ แต่ได้ไปพบกับข้อมูลพื้นที่ป่าของทั้งประเทศ
ซึ่งมีขนาดใหญ่เกินจำเป็นอย่างมาก
จึงจำเป็นต้องทำการดึงข้อมูลพื้นที่ของป่าควนเคร็งออกจากพื้นที่ป่าทั้งหมดเพื่อที่จะได้นำไปใช้งานต่อไป

### แนวทางแก้ไขปัญหา

ทำการดึงข้อมูลพื้นที่ป่าที่ต้องการออกมาจาพื้นที่ป่าทั้งหมด
ขั้นตอนแรกคือต้องทำการวัดขอบเขตโดยประมาณของพื้นที่ป่าที่ต้องการ
โดยพื้นที่ป่านั้นได้ทำการจากประมาณจากพื้นที่ป่าพรุที่สามารถพบได้จากพิกัดบริเวณ
(7.928282, 100.146664) โดยอ้างอิงจากแผนที่ป่าจาก <https://gfms.gistda.or.th/map>
และทำการคัดเอาเฉพาะพื้นที่ป่าที่อยู่ภายในขอบเขตจากการวัดก่อนหน้านี้
โดยข้อมูลพื้นที่ป่าทั้งหมดนั้นมาในรูปแบบ shapefile
ซึ่งใน shapefile นั้นประกอบด้วยรูปร่างย่อยที่เป็นรูปร่างประมาณของป่าต่างๆ
ทั้งหมดรวมแล้วนับได้ประมาณ 90000 รูปร่างย่อย
จึงจำเป็นที่จะต้องเขียนโปรแกรมนอกช่วยในการคัดกรองเพื่อที่จะเลือกเอารูปร่างป่าที่เกี่ยวข้องออกมา
พบว่าสามารถทำการดึงรูปร่างป่าควนเคร็งออกมาจากพื้นที่ป่าทั้งหมดได้
และสามารถบันทึกรูปร่างพื้นที่ป่าออกมาเพื่อนำไปใช้ต่อไปได้
หากมีความจำเป็นที่จะต้องใช้ข้อมูลรูปร่างป่าของพื้นที่อื่นก็สามารถทำการดึงข้อมูลออกมาได้ด้วยวิธีการเดียวกัน
