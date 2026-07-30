/*
  UHF RFID Get Version
 
 This example works only on the Arduino Mega 2560
 
 Serial port 1, connect to RFID module, baudrate = 115200
 Main Serial port, print Version msg, baudrate = 115200
 
 */
#define rfidSerial              Serial1

#define	RFID_FRAME_SOF1         0xA5
#define	RFID_FRAME_SOF2		0x5A
#define RFID_FRAME_EOF1		0x0D
#define RFID_FRAME_EOF2		0x0A

#define	RFID_FRAME_SOF_LEN	2
#define	RFID_FRAME_EOF_LEN	2
#define RFID_FRAME_LEN_LEN	2
#define	RFID_FRAME_CMD_LEN	1
#define	RFID_FRAME_CHK_LEN	1

#define RFID_FRAME_FIXED_LEN	(RFID_FRAME_SOF_LEN + RFID_FRAME_EOF_LEN + RFID_FRAME_LEN_LEN + RFID_FRAME_CMD_LEN + RFID_FRAME_CHK_LEN)

typedef enum
{
  RT_FALSE			 	 = 0,
  RT_TRUE			   	    ,
}
emReturnStateDef;

typedef struct
{
  byte			u8Sof1;			// header1
  byte			u8Sof2;			// header2
  byte			u8Len1;			// length
  byte			u8Len2;			// length
  byte 		        u8Cmd;			// cmd
  byte    		pData[250];
  byte                  u8Chk;			// CRC
  byte  		u8Eof1;			// end1
  byte			u8Eof2;			// end2
  byte			bCheckRet;
  byte       		bProcessing;
  byte       		bGetDataComplete;
}
stUartRecvFrameDef;

stUartRecvFrameDef stHostifRecvFrame;
byte u8HeadCnt = 0;	  // 帧头字节数
byte u8DataIdx = 0;	  // 接收帧数据索引
byte u8CalChk = 0;        // 计算校验值


// Calculate Frame check
byte Cal_Xor(byte *pBuf, int u16Len)
{
  byte	crc = 0;
  int	i;

  for (i=0; i<u16Len; i++)
  {
    crc ^= pBuf[i];
  }

  return crc;
}

// build rfid module communicate frame
int Build_RFID_Frame(byte u8Cmd, byte *pInData, int u16InLen, byte *pOutData, int *u16OutLen)
{
  int	cur = 0, i;

  /* frame header */
  pOutData[cur++] = RFID_FRAME_SOF1;
  pOutData[cur++] = RFID_FRAME_SOF2;
  /* length */
  pOutData[cur++] = ((u16InLen + RFID_FRAME_FIXED_LEN) >> 8) & 0xFF;
  pOutData[cur++] = (u16InLen + RFID_FRAME_FIXED_LEN) & 0xFF;
  /* cmd */
  pOutData[cur++] = u8Cmd;
  /* data */
  for (i=0; i<u16InLen; i++)
  {
    pOutData[cur++] = pInData[i];
  }
  /* frame check */
  pOutData[cur++] = Cal_Xor(&pOutData[2], (u16InLen+3));
  /* frame end */
  pOutData[cur++] = RFID_FRAME_EOF1;
  pOutData[cur++] = RFID_FRAME_EOF2;

  *u16OutLen = cur;

  return 0;
}

// serial send one frame data to rfid
void serialSendFrameToRFID(byte *sbuf, int len)
{
  rfidSerial.write(sbuf, len);
}

// Clear rfid serial buffer
void ClearrfidSerialReceiveBuffer(void)
{
  while(rfidSerial.read() >= 0) {
  }
}

// parse rfid frame
void Hostif_Parse_Frame(void)
{
  byte u8Data;

  if (rfidSerial.available() > 0)      // is receive data
  {	
    if (stHostifRecvFrame.bProcessing)
    {
      return;
    }

    u8Data = rfidSerial.read();

    if ( u8HeadCnt < 5 )				
    {
      switch (u8HeadCnt)	// get header data
      {
      case 0:																		// 帧头，高字节
        {
          if ( u8Data == RFID_FRAME_SOF1 )
          {
            u8HeadCnt++;
            stHostifRecvFrame.u8Sof1 	= u8Data;
          }
          break;		
        }
      case 1:																		// 帧头，低字节
        {
          if ( u8Data == RFID_FRAME_SOF2 )
          {
            u8HeadCnt++;
            stHostifRecvFrame.u8Sof2 = u8Data;
            u8CalChk = 0;
          }
          else
          {
            u8HeadCnt = 0;
          }
          break;		
        }

      case 2:																		// 帧长度，高字节
        {
          stHostifRecvFrame.u8Len1 = u8Data;
          u8HeadCnt++;
          u8CalChk 	^= u8Data;

          break;
        }

      case 3:																		// 帧长度，低字节
        {
          stHostifRecvFrame.u8Len2 = u8Data;
          u8HeadCnt++;
          u8CalChk ^= u8Data;	
          break;
        }

      case 4:																		// 帧类型
        {
          u8HeadCnt++;
          stHostifRecvFrame.u8Cmd = u8Data;
          u8CalChk ^= u8Data;

          u8DataIdx = 0;
          break;
        }
      }
    }
    else if (u8DataIdx < (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN))			// 帧数据
    {
      stHostifRecvFrame.pData[u8DataIdx++] = u8Data;
      u8CalChk ^= u8Data;
    }
    else if (u8DataIdx == (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN))			// CRC
    {
      if (u8CalChk != u8Data)									// check u8Data
      {
        u8HeadCnt = 0;
        u8CalChk = 0;
      }
      stHostifRecvFrame.u8Chk = u8Data;
      u8DataIdx++;
    }
    else if (u8DataIdx == (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN + 1))
    {
      if (u8Data == RFID_FRAME_EOF1)												// 帧尾，高字节
      {
        stHostifRecvFrame.u8Eof1 = u8Data;
        u8DataIdx++;
      }
      else
      {
        u8HeadCnt = 0;
        u8CalChk = 0;
      }
    }
    else if (u8DataIdx == (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN + 2))
    {
      if (u8Data == RFID_FRAME_EOF2)												// 帧尾，低字节
      {
        stHostifRecvFrame.u8Eof2 = u8Data;
        stHostifRecvFrame.bCheckRet = RT_TRUE;
        stHostifRecvFrame.bGetDataComplete = RT_TRUE; 		           
        stHostifRecvFrame.bProcessing = RT_TRUE;
      }
      else
      {
        stHostifRecvFrame.bCheckRet = RT_FALSE;
      }

      u8HeadCnt = 0;
      u8CalChk = 0;
      u8DataIdx	= 0;
    }
    else
    {
      u8HeadCnt = 0;
      u8CalChk = 0;
      u8DataIdx	= 0;
    }
  }
}

void setup() {

  Serial.begin(115200);
  rfidSerial.begin(115200);
}

// handle
byte Rfid_Handle_Command(void)
{
  byte	ret = RT_FALSE;

  if((stHostifRecvFrame.bGetDataComplete == RT_TRUE) && (stHostifRecvFrame.bCheckRet == RT_TRUE))
  {
    switch (stHostifRecvFrame.u8Cmd)
    {
    case 0x01:		// Get Hardware Version response
      {
        break;
      }

    default:	//其它命令直接透传
      break;
    }

    ret = RT_TRUE;

    stHostifRecvFrame.bProcessing = RT_FALSE;
    stHostifRecvFrame.bGetDataComplete = RT_FALSE;
  }

  return ret;
}

// get hardware version
byte GetHardwareVersion(byte *ver)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  Build_RFID_Frame(0x00, tmp, 0, sendbuf, &sendlen);      // cmd = 0x00
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x01)
      {
        memcpy(ver, stHostifRecvFrame.pData, 3);
        ret = RT_TRUE;
        break;
      }
    }
  }

  return ret;
}

// get firmware version
byte GetFirmwareVersion(byte *ver)            
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  Build_RFID_Frame(0x02, tmp, 0, sendbuf, &sendlen);        // cmd = 0x02
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x03)
      {
        memcpy(ver, stHostifRecvFrame.pData, 3);
        ret = RT_TRUE;
        break;
      }
    }
  }

  return ret;
}

// get deviceID
byte GetDeviceID(unsigned long *devid)            
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  Build_RFID_Frame(0x04, tmp, 0, sendbuf, &sendlen);        // cmd = 0x04
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x05)
      {
        *devid = ((unsigned long)stHostifRecvFrame.pData[0]<<24) + ((unsigned long)stHostifRecvFrame.pData[1]<<16) + (stHostifRecvFrame.pData[2]<<8) + (stHostifRecvFrame.pData[3]);

        ret = RT_TRUE;
        break;
      }
    }
  }

  return ret;
}

void loop() {
  byte hardver[3], firmver[3], result;

  Serial.println("GetHardwareVersion!");
  result = GetHardwareVersion(hardver);
  if (result == RT_TRUE)
  {
    Serial.println(hardver[0], DEC);
    Serial.println(hardver[1], DEC);
    Serial.println(hardver[2], DEC);
  }
  else
  {
    Serial.println("GetHardwareVersion failed!");
  }

  delay(1000);
  
  Serial.println("GetFirmwareVersion!");
  result = GetFirmwareVersion(firmver);
  if (result == RT_TRUE)
  {
    Serial.println(firmver[0], DEC);
    Serial.println(firmver[1], DEC);
    Serial.println(firmver[2], DEC);
  }
  else
  {
    Serial.println("GetFirmwareVersion failed!");
  }
  
  delay(1000);
  
  unsigned long deviceID;                  // 4bytes
  Serial.println("GetDeviceID!");
  result = GetDeviceID(&deviceID);
  if (result == RT_TRUE)
  {
    Serial.println(deviceID);
  }
  else
  {
    Serial.println("GetDeviceID failed!");
  }
  
  delay(1000);
}
